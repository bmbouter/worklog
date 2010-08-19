from django.contrib import admin
from django.contrib.auth.models import User

from worklog.models import WorkItem
#import worklog.admin_filter

class WorkItemAdmin(admin.ModelAdmin):
    list_display = ('user','date','hours','text')
    list_filter = ('user','date')

admin.site.register(WorkItem, WorkItemAdmin)

#class UserAdmin(admin.ModelAdmin):
#    list_filter = ()

