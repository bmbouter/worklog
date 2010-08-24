from django.contrib import admin
from django.contrib.auth.models import User

from worklog.models import WorkItem, Job, WorkLogReminder
#import worklog.admin_filter

class WorkItemAdmin(admin.ModelAdmin):
    list_display = ('user','date','hours','text','job')
    list_filter = ('user','date','job')

class JobAdmin(admin.ModelAdmin):
    list_display = ('name','open_date','close_date')
    #list_filter = ('',)

admin.site.register(WorkItem, WorkItemAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(WorkLogReminder)

#class UserAdmin(admin.ModelAdmin):
#    list_filter = ()

