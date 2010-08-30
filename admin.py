from django.contrib import admin
from django.contrib.auth.models import User

from django.http import HttpResponse
import csv
import operator

from worklog.models import WorkItem, Job, WorkLogReminder


class WorkItemAdmin(admin.ModelAdmin):
    list_display = ('user','date','hours','text','job')
    list_filter = ('user','date','job')
    
    def changelist_view(self, request, extra_context=None):
        # Look for 'export_as_csv' in the HTTP Request header.  If it is found, 
        # we export CSV.  If it is not found, defer to the super class.
        if 'export_as_csv' in request.POST:
            def getusername(item):
                if item.user.last_name:
                    return '{0} {1}'.format(item.user.first_name,item.user.last_name)
                # if no first/last name available, fall back to username
                else:
                    return item.user.username
            
            csvfields = [
                # Title, function on item returning value
                ('User Key',operator.attrgetter('user.pk')),
                ('User Name',getusername),
                ('Job',operator.attrgetter('job.name')),
                ('Date',operator.attrgetter('date')),
                ('Hours',operator.attrgetter('hours')),
                ('Task',operator.attrgetter('text')),
                ]
            
            ChangeList = self.get_changelist(request)
            
            # see django/contrib/admin/views/main.py  for ChangeList class.
            cl = ChangeList(request, self.model, self.list_display, self.list_display_links, self.list_filter,
                self.date_hierarchy, self.search_fields, self.list_select_related, self.list_per_page, self.list_editable, self) 
                
            header = list(s[0] for s in csvfields)
            rows = [header]
            # Iterate through currently displayed items.
            for item in cl.query_set:
                row = list(s[1](item) for s in csvfields)
                rows.append(row)
            
            response = HttpResponse(mimetype='text/csv')
            response['Content-Disposition'] = 'attachment; filename=somefilename.csv'
            
            writer = csv.writer(response)
            for row in rows:
                writer.writerow(row)

            return response

        else:
            return super(WorkItemAdmin,self).changelist_view(request, extra_context)

class JobAdmin(admin.ModelAdmin):
    list_display = ('name','open_date','close_date')

admin.site.register(WorkItem, WorkItemAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(WorkLogReminder)

