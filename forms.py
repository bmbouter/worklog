from django.forms import ModelForm, Select, Form, HiddenInput, Textarea
from django import forms
from worklog.models import WorkItem, Job #, WorkLogReminder

import datetime

#class WorkItemForm(ModelForm):
#    class Meta:
#        model = WorkItem
#        exclude = ['user','date']

class BadWorkItemForm(Exception):
    pass

class WorkItemForm(Form):
    hours = forms.IntegerField()
    text = forms.CharField(widget=Textarea)
    job = forms.ModelChoiceField(queryset=Job.objects.filter(name="")) # empty queryset, overridden in ctor   
#    job = forms.ModelChoiceField(queryset=Job.get_jobs_open_on(datetime.date.today()))
    #reminder_id = forms.CharField(widget=HiddenInput, max_length=36, required=False)

    def __init__(self, *args, **kwargs):
        #queryset = kwargs.pop("available_jobs")
        #reminder_id = kwargs.pop("reminder_id")
        reminder = kwargs.pop("reminder")
        super(WorkItemForm,self).__init__(*args,**kwargs)
        #self.fields["reminder_id"].initial = reminder_id
        #print "{0}".format(type(queryset))
        
        if reminder:
            queryset = reminder.get_available_jobs()
        else:
            queryset = Job.get_jobs_open_on(datetime.date.today())
        
        self.fields["job"].queryset = queryset

