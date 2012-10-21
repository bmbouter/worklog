import datetime
import calendar
import time
import re

from celery.execute import send_task

from django.utils import simplejson
from django.core import serializers
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User
from django.views.generic import View, TemplateView
from django.conf import settings

from worklog.forms import WorkItemForm
from worklog.models import WorkItem, WorkLogReminder, Job, Funding, Holiday, BiweeklyEmployee
from worklog.tasks import generate_invoice

# 'columns' determines the layout of the view table
_column_layout = [
    # key, title
    ('user','User'),
    ('date','Date'),
    ('hours','Hours'),
    ('job','Job'),
    ('text','Task'),
    ]
    
def _itercolumns(item):
    for key,title in _column_layout:
        yield getattr(item,key)

no_reminder_msg = 'There is no stored reminder with the given id.  Perhaps that reminder was already used?'

class BadReminderId(Exception):
    pass

def validate_reminder_id(request, reminder_id):
    # returns a tuple: (reminder, date)
    if not reminder_id:
        return (None,datetime.date.today())
    rems = WorkLogReminder.objects.filter(reminder_id=reminder_id)
    if not rems:
        raise BadReminderId(no_reminder_msg)
    if request.user != rems[0].user:
        raise BadReminderId('The current user name does not match the user saved with the given id.')
    date = rems[0].date
    return (rems[0],date)

def createWorkItem(request, reminder_id=None):
    try:
        reminder,date = validate_reminder_id(request, reminder_id)
    except BadReminderId as e:
        resp = HttpResponse(e.args)
        resp['Worklog-UnableToCreateItem'] = '' # for testing purposes
        return resp
    
    if request.method == 'POST': # If the form has been submitted...
        form = WorkItemForm(request.POST, reminder=reminder, logged_in_user=request.user)
        if form.is_valid():
            # get form data
            hours = form.cleaned_data['hours']
            text = form.cleaned_data['text']
            job = form.cleaned_data['job']
            # create then save an item
            wi = WorkItem(user=request.user, date=date, hours=hours, text=text, job=job)
            wi.save()
            if 'submit_and_add_another' in request.POST:
                # redisplay workitem form so another item may be added
                return HttpResponseRedirect(request.path)
            else:
                if date==datetime.date.today():
                    return HttpResponseRedirect('/worklog/view/%s/today/' % request.user.username) # Redirect after POST
                else:
                    return HttpResponseRedirect('/worklog/view/%s/%s_%s/' % ( request.user.username, date, date))
    else:
        form = WorkItemForm(reminder=reminder, logged_in_user=request.user) # An unbound form
        
    items = WorkItem.objects.filter(date=date, user=request.user)
    rawitems = list(tuple(_itercolumns(item)) for item in items)

    if BiweeklyEmployee.objects.filter(user=request.user).count() > 0:
        holidays = Holiday.objects.filter(start_date__gte=date, end_date__lte=date)
    else:
        holidays = None

    return render_to_response('worklog/workform.html',
            {'form': form, 'reminder_id': reminder_id, 'date': date,
             'items': rawitems, 
             'column_names': list(t for k,t in _column_layout),
             'holidays': holidays
            },
            context_instance=RequestContext(request)
        )
                            
def make_month_range(d):
    # take a date, return a tuple of two dates.  The day in the second date is the last day in that month.
    return (d, d.replace(day=calendar.monthrange(d.year, d.month)[1]))
    
class WorkViewMenu(object):
    class MenuItem(object):
        def __init__(self, querystring, name):
            self.querystring = querystring
            self.name = name
    class SubMenu(object):
        def __init__(self, name, items=None):
            """ name:  may be the empty string
            """
            self.name = name
            assert items is None or isinstance(items, list)
            # special handling if 'items' contains tuples
            if items and not isinstance(items[0], WorkViewMenu.MenuItem):
                items = list(WorkViewMenu.MenuItem(q,n) for q,n in items)
            self.items = items  if items else  []
            assert all(isinstance(item,WorkViewMenu.MenuItem) for item in self.items)
                
        def __iter__(self):
            return self.items.__iter__()
    def __init__(self):
        self.submenus = []
    def __iter__(self):
        return self.submenus.__iter__()
        
        
class WorkViewerFilter(object):
    def __init__(self, key, title, filter_lookup, query_fmtstring="{0}={1}", model=None, error_name="ERROR", name_attr=None):
        self.key = key
        self.title = title
        self.filter_lookup = filter_lookup
        self.query_fmtstring = query_fmtstring
        self.model = model
        self.value = None
        #self.error_value = None
        self.error_name = error_name
        self.display_name = self.error_name
        self.name_attr = name_attr
    
    def set_value(self, value):
        # validate?
        self.value = self.validate(value)
        
    def validate(self, value):
        return value
        
    def get_query_string(self):
        return "{0}={1}".format(self.key,self.value)  if self.value is not None else  ""
        
    def get_query_info(self):
        if self.value is not None:
            if self.model:
                qs = self.model.objects.filter(pk=self.value)
                name = getattr(qs[0], self.name_attr)  if qs.exists() else  self.error_name
            else:
                name = self.value
            return (self.title,"{0}".format(name))
        return None
            
    def apply_filter(self, items):
        if self.value is not None:
            items = items.filter(**{self.filter_lookup: self.value})
        return items
        
class WorkViewerDateFilter(WorkViewerFilter):
    def __init__(self, key, title, filter_lookup, error_value):
        super(WorkViewerDateFilter, self).__init__(key, title, filter_lookup)
        self.error_value = error_value  # is set in case of validation error
    def validate(self, value):
        if not isinstance(value, datetime.date):
            try:
                return datetime.date(*time.strptime(value,"%Y-%m-%d")[:3])
            except ValueError:
                return self.error_value
        return value
    

class WorkViewer(object):
    keys = ["user","job","datemin","datemax"]
    
    def __init__(self, request, username, datemin, datemax):
        self.filters = {}
        self.filters["user"] = WorkViewerFilter("user","User","user",model=User,error_name="<unknown_user>",name_attr="username")
        self.filters["job"] = WorkViewerFilter("job","Job","job",model=Job,error_name="<unknown_job>",name_attr="name")
        self.filters["datemin"] = WorkViewerDateFilter("datemin","Date minimum","date__gte",error_value=datetime.date.min)
        self.filters["datemax"] = WorkViewerDateFilter("datemax","Date maximum","date__lte",error_value=datetime.date.max)
        
        userid=None
        # convert username to userid
        if username:
            qs = User.objects.filter(username=username)
            userid = qs[0].pk  if qs.exists() else  -1
        # raw HTTP request info
        for key in self.keys:
            if key in request.GET: 
                self.filters[key].set_value( request.GET[key] )
        # also process arguments
        for key,val in [("user",userid),("datemin",datemin),("datemax",datemax)]:
            if val is not None: 
                self.filters[key].set_value( val )
        
        self.current_queries = {}
        # Save current queries to use when creating links.
        for filter in self.filters.itervalues():
            q = filter.get_query_string()
            if q:
                self.current_queries[filter.key] = q
            
        self.menu = WorkViewMenu()
        allsubmenu = WorkViewMenu.SubMenu("",[WorkViewMenu.MenuItem("","all")])
        self.menu.submenus.append(allsubmenu)
        
        # build the links
        self.build_user_links()
        self.build_job_links()
        self.build_yearmonth_links()
        
        # query info... for display in the web page
        self.query_info = []
        for key in self.keys:
            qi = self.filters[key].get_query_info()
            if qi is not None:
                self.query_info.append(qi)
            
            
    def filter_items(self, items):
        for filter in self.filters.itervalues():
            items = filter.apply_filter(items)
        return items
        
        
    def build_user_links(self):
        # The basequery includes all current queries except for 'user'
        basequery = '&'.join(v for k,v in self.current_queries.iteritems() if k!="user")
        alllink = (basequery,'all users')
        if basequery: basequery+='&'
        links = list(("{1}user={0}".format(user.pk,basequery),user.username) for user in User.objects.all())
        links = [alllink] + links
        self.menu.submenus.append(WorkViewMenu.SubMenu("User",links))
        
    def build_yearmonth_links(self):
        basequery = '&'.join(v for k,v in self.current_queries.iteritems() if k!="datemin" and k!="datemax")
        alllink = (basequery,'all dates')
        if basequery: basequery+='&'
        
        # get all dates
        values_list = WorkItem.objects.values_list('date', flat=True)
        # Strip the day from dates and remove duplicates.
        unique_dates = list(set(
            val.replace(day=1) for val in values_list if isinstance(val, datetime.date)
            ))
        # Sort so most recent date is at the top.
        unique_dates.sort(reverse=True)
        ranges = list(make_month_range(x) for x in unique_dates)
        
        links = list(("{2}datemin={0}&datemax={1}".format(a,b,basequery),a.strftime('%Y %B')) for a,b in ranges)
        links = [alllink] + links
        self.menu.submenus.append(WorkViewMenu.SubMenu("Date",links))
        
    def build_job_links(self):
        basequery = '&'.join(v for k,v in self.current_queries.iteritems() if k!="job")
        alllink = (basequery,'all jobs')
        if basequery: basequery+='&'
        links = list(("{1}job={0}".format(job.pk,basequery),job.name) for job in Job.objects.all())
        links = [alllink] + links
        self.menu.submenus.append(WorkViewMenu.SubMenu("Job",links))
    
def viewWork(request, username=None, datemin=None, datemax=None):
    if datemin=='today':  datemin = datetime.date.today()
    if datemax=='today':  datemax = datetime.date.today()
    
    viewer = WorkViewer(request,username,datemin,datemax)
    
    items = WorkItem.objects.all()
    items = viewer.filter_items(items)
    
    # menulink_base must either be blank, or include a trailing slash.
    # menulink_base is the part of the URL in the menu links that will precede the '?'
    menulink_base = ''
    if username is not None: menulink_base += '../'
    if datemin or datemax: menulink_base += '../'
    
    rawitems = list(tuple(_itercolumns(item)) for item in items)
    
    return render_to_response('worklog/viewwork.html', 
            {'items': rawitems,
             'filtermenu': viewer.menu,
             'menulink_base': menulink_base,
             'column_names': list(t for k,t in _column_layout),
             'current_filters': viewer.query_info,
            },
            context_instance=RequestContext(request)
        )
    

class ReportView(TemplateView):
    template_name = 'worklog/report.html'
    
    def get_context_data(self, **kwargs):
        context = super(ReportView, self).get_context_data()
        context['date'] = kwargs.get('date', None)

        return context

    def get(self, request, *args, **kwargs):
        if 'date' in request.GET:
            try:
                date = request.GET['date']
                date_time = datetime.datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                date = datetime.date.today()
                return self.render_to_response({
                    'error': 'Date not correct format: yyyy-mm-dd. Using today as default date.',
                    'date': date
                })
        else:
            date = unicode(datetime.date.today())

        return self.render_to_response({'date': date})

    def post(self, request, *args, **kwargs):
        date = request.POST['date']
        
        if 'generate' in request.POST:
            generate_invoice.delay(date)
            #send_task("tasks.generate_invoice")
            return self.render_to_response({'generated': True, 'date': date})
        elif 'invoice' in request.POST:
            jobs = Job.objects.filter(billing_schedule__date=date)
            
            for job in jobs:
                work_items = WorkItem.objects.filter(job=job, invoiced=False, date__lt=date).exclude(do_not_invoice=True)
                for items in work_items:
                    items.invoiced = True
                    items.save()
            return self.render_to_response({'invoiced': True, 'date': date})
        else:
            return self.render_to_response(self.get_context_data(**kwargs))

    def render_to_response(self, context):
        return TemplateView.render_to_response(self, context)

class ChartView(TemplateView):
    template_name = 'worklog/chart.html'

    #@method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(ChartView, self).dispatch(*args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        if 'job_id' in request.GET:
            job_id = request.GET['job_id']
            
            if 'start_date' in request.GET:
                start_date = request.GET['start_date']
            else:
                start_date = None
            
            if 'end_date' in request.GET:
                end_date = request.GET['end_date']
            else:
                end_date = None
                
            context['start_date'] = start_date
            context['end_date'] = end_date
            context['job_id'] = job_id
            
            return self.render_to_response(context)
        else:
            return self.render_to_response(context)
        
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs);
        
        job_id = request.POST['job_id']
        start_date = None
        end_date = None
        
        # Make sure the use selected a job
        if job_id == '-1':
            return self.error('Invalid job selection')
            #error = { }
            #error['error'] = 'Invalid job selection'
            #return HttpResponse(simplejson.dumps(data), mimetype='application/json')
        
        # Check if the job doesnt exist due to a bad param
        try:
            job = Job.objects.get(pk=job_id)
        except:
            return self.error('Job with id %s does not exist' % job_id)
            #error = { }
            #error['error'] = 'Job with id %s does not exist' % job_id
            #return HttpResponse(simplejson.dumps(error), mimetype='application/json')
        
        if job is not None:
            data = {}
            start_date = None
            end_date = None

            if job.hasFunding():
                funding = Funding.objects.filter(job=job)
            else:
                funding = None
                
            if job.hasWork():
                work_items = WorkItem.objects.filter(job=job)
            else:
                work_items = None
            
            # Try to convert the dates given
            if 'start_date' in request.POST:
                if len(request.POST['start_date']) > 0:
                    try:
                        start_date = datetime.datetime.strptime(request.POST['start_date'], '%m/%d/%Y').date()
                    except ValueError:
                        return self.error('Enter a valid date format for the start date')
                        #error = { }
                        #error['error'] = 'Enter a valid date format'
                        #return HttpResponse(simplejson.dumps(error), mimetype='application/json')
                else:
                    if funding is None and work_items is None:
                        return self.error('There is no work or funding available for job %s' % job)
                    else:
                        if funding is not None:
                            first_funding = funding.order_by('date_available')[0].date_available
                        else:
                            first_funding = None
                        
                        if work_items is not None:
                            first_work = work_items.order_by('date')[0].date
                        else:
                            first_work = None
                    
                    if first_work is not None and first_funding is not None:
                        if first_work > first_funding:
                            start_date = first_funding
                        else:
                            start_date = first_work
                    elif first_work is None and first_funding is not None:
                        start_date = first_funding
                    elif first_work is not None and first_funding is None:
                        start_date = first_work
                    else:
                        return self.error('There is no work or funding available for job %s' % job)
            
            if 'end_date' in request.POST:
                if len(request.POST['end_date']) > 0:
                    try:
                         end_date = datetime.datetime.strptime(request.POST['end_date'], '%m/%d/%Y').date()
                    except ValueError:
                         return self.error('Enter a valid date format for the end date')
                         #error = { }
                         #error['error'] = 'Enter a valid date format'
                         #return HttpResponse(simplejson.dumps(error), mimetype='application/json')
                else:
                    if funding is None and work_items is None:
                        return self.error('There is no work or funding available for job %s' % job)
                    else:
                        if funding is not None:
                            last_funding = funding.latest('date_available').date_available
                        else:
                            last_funding = None
                        
                        if work_items is not None:
                            last_work = work_items.latest('date').date
                        else:
                            last_work = None
                            
                    if last_work is not None and last_funding is not None:
                        if last_work < last_funding:
                            end_date = last_funding
                        else:
                            end_date = last_work
                    elif last_work is None and last_funding is not None:
                        end_date = last_funding
                    elif last_work is not None and last_funding is None:
                        end_date = last_work
                    else:
                        return self.error('There is no work or funding available for job %s' % job)
                    
            # If, somehow, the dates were not set, do not continue
            if start_date is not None and end_date is not None:
                hours = 0
                
                date = start_date
                days = (end_date - start_date).days
                
                # Make sure the dates were in a valid order
                if days < 0:
                    return self.error('Start date has to be before end date')
                    #error = { }
                    #error['error'] = 'Start date has to be before end date'
                    #return HttpResponse(simplejson.dumps(error), mimetype='application/json')
                else:
                    # We need to calculate the hours since the first available funding
                    # or first work item
                    if work_items is not None:
                        work_date = work_items.order_by('date')[0].date
                    else:
                        work_date = None
                        
                    if funding is not None:
                        funding_date = funding.order_by('date_available')[0].date_available
                    else:
                        funding_date = None    
                        
                    if work_date is not None and funding_date is not None:
                        if funding_date < work_date:
                            initial_date = funding_date
                        else:
                            initial_date = work_date
                    elif funding_date is None and work_date is not None:
                        initial_date = work_date
                    elif work_date is None and funding_date is not None:
                        initial_date = funding_date
                    else:
                        return self.error('There is no work or funding available for job %s' % job)
                        #error = { }
                        #error['error'] = 'There is no work or funding available for job %s' % job
                        #return HttpResponse(simplejson.dumps(error), mimetype='application/json')
                    
                    initial_days = (start_date - initial_date).days
                    
                    # If we have a difference between the initial date and start date
                    # then we need to calculate up to the initial days
                    if initial_days > 0:
                        if funding is not None:
                            initial_hours = funding.order_by('date_available')[0].hours
                        else:
                            initial_hours = 0
                        initial_hours = 0
                        for n in range(initial_days):
                            if work_items is not None:
                                for work_item in work_items.filter(date=initial_date):
                                    hours -= work_item.hours
                            
                            if funding is not None:
                                for funds in funding.filter(date_available=initial_date):
                                    hours += funds.hours
                                
                            initial_date += datetime.timedelta(days=1)
                    
                    # Loop through and calculate the hours for each day
                    for n in range(days + 1):
                        if work_items is not None:
                            for work_item in work_items.filter(date=date):
                                hours -= work_item.hours
                        
                        if funding is not None:
                            for funds in funding.filter(date_available=date):
                                hours += funds.hours
                        
                        data[str(date)] = hours
                        date += datetime.timedelta(days=1)

                    return HttpResponse(simplejson.dumps(data), mimetype='application/json')
            else:
                return self.error('Dates could not be processed')
                #error = { }
                #error['error'] = 'Dates could not be processed'
                #return HttpResponse(simplejson.dumps(error), mimetype='application/json')
        else:
            return self.error('That job does not exist')
            #error = { }
            #error['error'] = 'That job does not exist'
            #return HttpResponse(simplejson.dumps(error), mimetype='application/json')  
    
    def error(self, message):
        error = { }
        error['error'] = message
        return HttpResponse(simplejson.dumps(error), mimetype='application/json')  
    
    def get_context_data(self, **kwargs):
        context = super(ChartView, self).get_context_data()
        context['open_jobs'] = (Job.objects.filter(close_date__gt=datetime.date.today()) \
            | Job.objects.filter(close_date=None)).order_by('name')
        context['closed_jobs'] = Job.objects.filter(close_date__lte=datetime.date.today()).order_by('name')

        return context

    def render_to_response(self, context):
        return TemplateView.render_to_response(self, context)


class JobDataView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(JobDataView, self).dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        if 'date' in request.POST and 'job_id' in request.POST:
            job_id = request.POST['job_id']
            date_in_millis = str(request.POST['date'])
            
            if '.' in date_in_millis:
                date_in_millis = int(str(date_in_millis).split('.')[0])
            
            # Look into why this is occurring
            # The milliseconds are a whole day behind, add one day
            date = datetime.datetime.fromtimestamp(date_in_millis//1000) + datetime.timedelta(days=1)
            work_items = WorkItem.objects.filter(job__pk=job_id, date=date.date())
            data = serializers.serialize('json', work_items)
            
            return HttpResponse(data, mimetype='application/json')



