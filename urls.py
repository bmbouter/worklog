import datetime

from django.conf.urls.defaults import *

##DATEMIN = r'(?P<datemin>\d{4}-\d{2}-\d{2})'
##DATEMAX = r'(?P<datemax>\d{4}-\d{2}-\d{2})'
# accepts:  date_date   or   date_   or   _date
##DATERANGE = '(?:'+DATEMIN+'_'+DATEMAX+'|'DATEMIN+'_'+'|_'+DATEMAX+')'

##USERNAME = r'(?P<username>([a-zA-Z0-9])+)'
##JOBID = r'(?:_job_(?P<jobid>[0-9]+))'

urlpatterns = patterns('worklog',
    (r'^add/$', 'views.createWorkItem', {'reminder_id': None}),
    (r'^add/reminder_(?P<reminder_id>[0-9a-f\-]{36})/$','views.createWorkItem'),
    
    (r'^view/$', 'views.viewWork'),
    (r'^view/today/$', 'views.viewWork', {'date': datetime.date.today()}),
    (r'^view/(?P<date>(\d{4}-\d{2}-\d{2}){1})/$', 'views.viewWork'),
    (r'^view/(?P<username>([a-zA-Z0-9])+)/$', 'views.viewWork'),
    (r'^view/(?P<username>([a-zA-Z0-9])+)/today/$', 'views.viewWork', {'date': datetime.date.today()}),
    (r'^view/(?P<username>([a-zA-Z0-9])+)/(?P<date>(\d{4}-\d{2}-\d{2}){1})/$', 'views.viewWork'),
    
    # (r'^view/$', 'views.viewWork'),
    # (r'^view/today/$', 'views.viewWork', {'datemin': datetime.date.today(), 'datemax': datetime.date.today()}),
    # (r'^view/'+DATERANGE+'/$', 'views.viewWork'),
    # (r'^view/'+USERNAME+'/$', 'views.viewWork'),
    # (r'^view/'+JOBID+'/$', 'views.viewWork'),
    # (r'^view/(?P<username>([a-zA-Z0-9])+)/today/$', 'views.viewWork', {'date': datetime.date.today()}),
    # (r'^view/(?P<username>([a-zA-Z0-9])+)/(?P<date>(\d{4}-\d{2}-\d{2}){1})/$', 'views.viewWork'),
)
