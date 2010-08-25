from django.contrib import admin
from django.contrib.auth.models import User

from django.http import HttpResponse
import csv

from worklog.models import WorkItem, Job, WorkLogReminder
#import worklog.admin_filter

def export_csv(modeladmin, request, queryset):
    pass
export_csv.short_description = "Save the selected Work Items to a CSV file."

class WorkItemAdmin(admin.ModelAdmin):
    list_display = ('user','date','hours','text','job')
    list_filter = ('user','date','job')
    
    def changelist_view(self, request, extra_context=None):
        if 'export_as_csv' in request.POST:
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = 'attachment; filename=somefilename.csv'
            
            ChangeList = self.get_changelist(request)
            
            cl = ChangeList(request, self.model, self.list_display, self.list_display_links, self.list_filter,
                self.date_hierarchy, self.search_fields, self.list_select_related, self.list_per_page, self.list_editable, self) 
                
            rows = []
            for item in cl.query_set:
                row = list()
                row.append(str(item.user.pk))
                # if no first/last name available, fall back to username
                if item.user.last_name:
                    row.append('{0} {1}'.format(item.user.first_name,item.user.last_name))
                else:
                    row.append(item.user.username)
                row.append(item.job.name)
                row.append(str(item.date))
                row.append(str(item.hours))
                row.append(item.text)
                rows.append(row)
            
            writer = csv.writer(response)
            for row in rows:
                writer.writerow(row)

            return response

        else:
            return super(WorkItemAdmin,self).changelist_view(request, extra_context)

class JobAdmin(admin.ModelAdmin):
    list_display = ('name','open_date','close_date')
    #list_filter = ('',)

admin.site.register(WorkItem, WorkItemAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(WorkLogReminder)

#class UserAdmin(admin.ModelAdmin):
#    list_filter = ()

