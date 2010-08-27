import datetime
import calendar

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from worklog.forms import WorkItemForm
from worklog.models import WorkItem, WorkLogReminder, Job

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


@login_required
def createWorkItem(request, reminder_id=None):
    try:
        reminder,date = validate_reminder_id(request, reminder_id)
    except BadReminderId as e:
        resp = HttpResponse(e.args)
        resp['Worklog-UnableToCreateItem'] = '' # for testing purposes
        return resp
    
    if request.method == 'POST': # If the form has been submitted...
        form = WorkItemForm(request.POST, reminder=reminder)
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
        form = WorkItemForm(reminder=reminder) # An unbound form

    return render_to_response('worklog/workform.html',
            {'form': form, 'reminder_id': reminder_id},
                            context_instance=RequestContext(request))
                            
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
            # special handling if 'items' contains tuples
            assert items is None or isinstance(items, list)
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
    

class WorkViewer(object):
    keys = ["user","job","datemin","datemax"]
    
    def __init__(self, request, username, datemin, datemax):
        userid=None
        # convert username to userid
        if username:
            qs = User.objects.filter(username=username)
            if qs.exists():
                userid = qs[0].pk
        self.selected = {}
        # raw HTTP request info
        for key in self.keys:
            if key in request.GET:   self.selected[key] = request.GET[key]
        # also process arguments
        for key,val in [("user",userid),("datemin",datemin),("datemax",datemax)]:
            if val is not None: self.selected[key] = val
            
        # handle invalid ids:
        if "user" in self.selected: 
            if not User.objects.filter(pk=self.selected["user"]).exists():
                del self.selected["user"]
        if "job" in self.selected: 
            if not Job.objects.filter(pk=self.selected["job"]).exists():
                del self.selected["job"]
        
        self.current_queries = {}
        # Save current queries to use when creating links.
        for key,val in self.selected.iteritems():
            self.current_queries[key] = "{0}={1}".format(key,val)
            
        self.menu = WorkViewMenu()
        allsubmenu = WorkViewMenu.SubMenu("",[WorkViewMenu.MenuItem("","all")])
        self.menu.submenus.append(allsubmenu)
        
        # build the links
        self.build_user_links(request)
        self.build_job_links(request)
        self.build_yearmonth_links(request)
        
        # query info... for display in the web page
        self.view_filters = []
        if "user" in self.selected:
            val = self.selected["user"]
            self.view_filters.append(('User',"{0}".format(User.objects.filter(pk=val)[0].username)))
        if "job" in self.selected:
            val = self.selected["job"]
            self.view_filters.append(("Job", "{0}".format(Job.objects.filter(pk=val)[0].name)))
        if "datemin" in self.selected:
            val = self.selected["datemin"]
            self.view_filters.append(("Date minimum", "{0}".format(val)))
        if "datemax" in self.selected:
            val = self.selected["datemax"]
            self.view_filters.append(("Date maximum", "{0}".format(val)))
            
            
    def filter_items(self, items):
        if "user" in self.selected:
            items = items.filter(user__pk=self.selected["user"])
        if "job" in self.selected:
            items = items.filter(job__pk=self.selected["job"])
        if "datemin" in self.selected:
            items = items.filter(date__gte=self.selected["datemin"])
        if "datemax" in self.selected:
            items = items.filter(date__lte=self.selected["datemax"])
        return items
        
        
    def build_user_links(self, request):
        # The basequery includes all current queries except for 'user'
        basequery = '&'.join(v for k,v in self.current_queries.iteritems() if k!="user")
        alllink = (basequery,'all users')
        if basequery: basequery+='&'
        links = list(("{1}user={0}".format(user.pk,basequery),user.username) for user in User.objects.all())
        links = [alllink] + links
        self.menu.submenus.append(WorkViewMenu.SubMenu("User",links))
        
    def build_yearmonth_links(self, request):
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
        
    def build_job_links(self, request):
        basequery = '&'.join(v for k,v in self.current_queries.iteritems() if k!="job")
        alllink = (basequery,'all jobs')
        if basequery: basequery+='&'
        links = list(("{1}job={0}".format(job.pk,basequery),job.name) for job in Job.objects.all())
        links = [alllink] + links
        self.menu.submenus.append(WorkViewMenu.SubMenu("Job",links))
    

def viewWork(request, username=None, datemin=None, datemax=None):
    viewer = WorkViewer(request,username,datemin,datemax)
    
    items = WorkItem.objects.all()
    items = viewer.filter_items(items)
    
    # menulink_base must either be blank, or include a trailing slash.
    # menulink_base is the part of the URL in the menu links that will precede the '?'
    menulink_base = ''
    if username is not None: menulink_base += '../'
    if datemin or datemax: menulink_base += '../'
    
    # 'columns' determines the layout of the view table
    columns = [
        # key, title
        ('user','User'),
        ('date','Date'),
        ('hours','Hours'),
        ('job','Job'),
        ('text','Task'),
        ]
    
    def itercolumns(item):
        for key,title in columns:
            yield getattr(item,key)
    
    rawitems = list(tuple(itercolumns(item)) for item in items)
    
    return render_to_response('worklog/viewwork.html', 
            {'items': rawitems,
             'filtermenu': viewer.menu,
             'menulink_base': menulink_base,
             'column_names': list(t for k,t in columns),
             'current_filters': viewer.view_filters,
            }
        )
    

