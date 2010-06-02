from django.forms import ModelForm, Select

from worklog.models import WorkItem

class WorkItemForm(ModelForm):
    class Meta:
        model = WorkItem
        widgets = {
            'user': Select(attrs={'disabled': 'disabled'}),
        }

