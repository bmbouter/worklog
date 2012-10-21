from django.forms import ModelForm, Select, Form, HiddenInput, Textarea
from django import forms
from worklog.models import WorkItem, Job 
from django.db.models import Q

import datetime


class BadWorkItemForm(Exception):
    pass

class WorkItemForm(Form):
    hours = forms.IntegerField()
    text = forms.CharField(widget=Textarea)
    job = forms.ModelChoiceField(queryset=Job.objects.filter(name="")) # empty queryset, overridden in ctor   

    def __init__(self, *args, **kwargs):
        reminder = kwargs.pop("reminder")
        user = kwargs.pop("logged_in_user");
        super(WorkItemForm,self).__init__(*args,**kwargs)
        
        if reminder:
            queryset = reminder.get_available_jobs()
        else:
            queryset = Job.get_jobs_open_on(datetime.date.today())
        
        queryset = queryset.filter(Q(available_all_users=True)|Q(users__id=user.id)).distinct()
        queryset = queryset.order_by('name')
        self.fields["job"].queryset = queryset
