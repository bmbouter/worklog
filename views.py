import datetime

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required

from worklog.forms import WorkItemForm
from worklog.models import WorkItem

import core
log = core.log.getLogger()

@login_required
def createWorkItem(request):
    log.warning(request.user)
    if request.method == 'POST': # If the form has been submitted...
        form = WorkItemForm(request.POST, instance=WorkItem(user=request.user))
        #form = WorkItemForm(request.POST) # A form bound to the POST data
        #new_work = form.save(commit=False)
        #new_work.user = request.user
        #form = WorkItemForm(instance=new_work) # The username in the form
        #return HttpResponse(form.user)
        if form.is_valid(): # All validation rules pass
            # Process the data in form.cleaned_data
            form.save()
            return HttpResponseRedirect('/worklog/add') # Redirect after POST
    else:
        f = WorkItemForm() # An unbound form
        new_work = f.save(commit=False)
        new_work.user = request.user
        form = WorkItemForm(instance=new_work) # The username in the form

    return render_to_response('worklog/workform.html',
                            {'form': form},
                            context_instance=RequestContext(request))
'''

def thanks(request):
    return HttpResponse('Thanks for the order!')
'''

def viewWork(request, date=None, user=None):
    log.warning('user = %s, and date = %s' % (user,date))
    if user:
        items = WorkItem.objects.filter(user=user)
        log.error(items)
        return HttpResponse('here')
    else:
        return HttpResponse('Ahere')
        items = WorkItem.objects.all()
    if date:
        return HttpResponse('Bhere')
        items = items.filter(date=date)
    return HttpResponse(items)
    return render_to_response('worklog/viewwork.html', {'items': items})
