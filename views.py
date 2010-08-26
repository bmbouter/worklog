import datetime
import calendar

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from worklog.forms import WorkItemForm
from worklog.models import WorkItem, WorkLogReminder, Job

#import opus.lib.log
#log = opus.lib.log.getLogger()

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
    
    #actsuffix = 'reminder_%s/'%(reminder_id,)


@login_required
def createWorkItem(request, reminder_id=None):
    #log.warning(request.user)
    try:
        reminder,date = validate_reminder_id(request, reminder_id)
    except BadReminderId as e:
        return HttpResponse(e.args)
    
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
                a,b = make_month_range(date.replace(day=1))
                dq = 'datemin={0}&datemax={1}'.format(a,b)
                return HttpResponseRedirect('/worklog/view/?user=%d&%s' % (request.user.pk,dq))
                # if date==datetime.date.today():
                    # return HttpResponseRedirect('/worklog/view/?user=%d' % request.user.pk) # Redirect after POST
                # else:
                    # return HttpResponseRedirect('/worklog/view/%s/%s/' % ( request.user.username, date))
    else:
        form = WorkItemForm(reminder=reminder) # An unbound form

    return render_to_response('worklog/workform.html',
            {'form': form, 'reminder_id': reminder_id},
                            context_instance=RequestContext(request))
                            
def make_month_range(d):
    # take a date, return a tuple of two dates.  The day in the second date is the last day in that month.
    return (d, d.replace(day=calendar.monthrange(d.year, d.month)[1]))

class WorkViewer(object):
    selected_userid = None
    selected_datemin = None
    selected_datemax = None
    selected_jobid = None
    
    def __init__(self, request):
        # raw HTTP request info
        self.selected_userid = request.GET.get("user",None)
        self.selected_jobid = request.GET.get("job",None)
        self.selected_datemin = request.GET.get("datemin",None)
        self.selected_datemax = request.GET.get("datemax",None)
        
        self.current_queries = {}
        # Save current queries to use when creating links.
        if self.selected_jobid is not None:
            self.current_queries["job"] = "job={0}".format(self.selected_jobid)
        if self.selected_userid is not None:
            self.current_queries["user"] = "user={0}".format(self.selected_userid)
        if self.selected_datemin is not None:
            self.current_queries["datemin"] = "datemin={0}".format(self.selected_datemin)
        if self.selected_datemax is not None:
            self.current_queries["datemax"] = "datemax={0}".format(self.selected_datemax)
            
        # build the links
        self.build_user_links(request)
        self.build_job_links(request)
        self.build_yearmonth_links(request)
            
    def filter_items(self, items):
        if self.selected_userid is not None:
            items = items.filter(user__pk=self.selected_userid)
        if self.selected_jobid is not None:
            items = items.filter(job__pk=self.selected_jobid)
        if self.selected_datemin:
            items = items.filter(date__gte=self.selected_datemin)
        if self.selected_datemax:
            items = items.filter(date__lte=self.selected_datemax)
        return items
        
    def build_user_links(self, request):
        # The basequery includes all current queries except for 'user'
        basequery = '&'.join(v for k,v in self.current_queries.iteritems() if k!="user")
        alllink = (basequery,'all users')
        if basequery: basequery+='&'
        self.userlinks = list(("{1}user={0}".format(user.pk,basequery),user.username) for user in User.objects.all())
        self.userlinks = [alllink] + self.userlinks
        
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
        # 
        ranges = list(make_month_range(x) for x in unique_dates)
        
        self.yearmonthlinks = list(("{2}datemin={0}&datemax={1}".format(a,b,basequery),a.strftime('%Y %B')) for a,b in ranges)
        self.yearmonthlinks = [alllink] + self.yearmonthlinks
        
    def build_job_links(self, request):
        basequery = '&'.join(v for k,v in self.current_queries.iteritems() if k!="job")
        alllink = (basequery,'all jobs')
        if basequery: basequery+='&'
        self.joblinks = list(("{1}job={0}".format(job.pk,basequery),job.name) for job in Job.objects.all())
        self.joblinks = [alllink] + self.joblinks
    
    

def viewWork(request):
    #log.warning('username = %s, and date = %s' % (username,date))
    
    viewer = WorkViewer(request)
    
    items = WorkItem.objects.all()
    items = viewer.filter_items(items)
        
    return render_to_response('worklog/viewwork.html', 
            {'items': items,
             'joblinks': viewer.joblinks,
             'userlinks': viewer.userlinks,
             'yearmonthlinks': viewer.yearmonthlinks,
            }
        )
    
'''

def thanks(request):
    return HttpResponse('Thanks for the order!')
'''

def old_viewWork(request, date=None, username=None):
    #log.warning('username = %s, and date = %s' % (username,date))
    if username:
        user_model = User.objects.filter(username=username)
        if user_model:
            items = WorkItem.objects.filter(user=user_model[0].pk)
        else:
            return HttpResponse('Username %s is invalid' % username)
    else:
        items = WorkItem.objects.all()
    if not items:
        return HttpResponse('The user %s has done no work' % username)
    if date:
        items = items.filter(date=date)
    return render_to_response('worklog/viewwork.html', {'items': items})
