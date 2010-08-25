import datetime

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
            hours = form.cleaned_data['hours']
            text = form.cleaned_data['text']
            job = form.cleaned_data['job']
            wi = WorkItem(user=request.user, date=date, hours=hours, text=text, job=job)
            wi.save()
            if 'submit_and_add_another' in request.POST:
                return HttpResponseRedirect(request.path)
            else:
                if date==datetime.date.today():
                    return HttpResponseRedirect('/worklog/view/%s/today/' % request.user.username) # Redirect after POST
                else:
                    return HttpResponseRedirect('/worklog/view/%s/%s/' % ( request.user.username, date))
            
#        form = WorkItemForm(request.POST, instance=WorkItem(user=request.user, date=datetime.date.today()))
#        if form.is_valid(): # All validation rules pass
#            # Process the data in form.cleaned_data
#            form.save()
#            return HttpResponseRedirect('/worklog/view/%s/today/' % request.user.username) # Redirect after POST
    else:
        form = WorkItemForm(reminder=reminder) # An unbound form

    #return HttpResponse('form = %s' % form)
    return render_to_response('worklog/workform.html',
            {'form': form, 'reminder_id': reminder_id},
                            context_instance=RequestContext(request))

# @login_required
# def createWorkItemReminder(request, reminder_id):    
    # rems = None
    # if not reminder_id:
        # return HttpResponse('Expected a reminder id.')
    # rems = WorkLogReminder.objects.filter(reminder_id=reminder_id)
    # if not rems:
        # return HttpResponse(no_reminder_msg)
    # if request.user != rems[0].user:
        # return HttpResponse('The current user name does not match the user saved with the given id.')
    # date = rems[0].date
    # actsuffix = 'reminder_%s/'%(reminder_id,)
    
    # if request.method == 'POST': # If the form has been submitted...
        # #item = WorkItem(user=request.user, date=date)
        # form = WorkItemForm(request.POST, available_jobs=Job.get_jobs_open_on(date), reminder_id=reminder_id)
        # if form.is_valid(): # All validation rules pass
            # # Process the data in form.cleaned_data
            # hours = form.cleaned_data['hours']
            # text = form.cleaned_data['text']
            # job = form.cleaned_data['job']
            # wi = WorkItem(user=request.user, date=date, hours=hours, text=text, job=job)
            # wi.save()
            # # When a user submits a form with a reminder_id, delete the record of the reminder_id
            # #rems[0].delete()
            # return HttpResponseRedirect('/worklog/view/%s/%s/' % (request.user.username, str(date))) # Redirect after POST
    # else:
        # form = WorkItemForm(available_jobs=Job.get_jobs_open_on(date), reminder_id=None) # An unbound form

    # #return HttpResponse('form = %s' % form)
    # return render_to_response('worklog/workform.html',
                              # {'form': form, 'actsuffix': actsuffix},
                              # context_instance=RequestContext(request))
'''

def thanks(request):
    return HttpResponse('Thanks for the order!')
'''

def viewWork(request, date=None, username=None):
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
