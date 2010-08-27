import datetime

from django.conf.urls.defaults import *

DATEMIN = r'(?P<datemin>\d{4}-\d{2}-\d{2})'
DATEMAX = r'(?P<datemax>\d{4}-\d{2}-\d{2})'
# accepts:  date_date   or   date_   or   _date
DATERANGE1 = '(?:'+DATEMIN+'_'+DATEMAX+'?)'
DATERANGE2 = '(?:_'+DATEMAX+')'

USERNAME = r'(?P<username>[a-zA-Z0-9]+)'
##JOBID = r'(?:_job_(?P<jobid>[0-9]+))'

urlpatterns = patterns('worklog',
    (r'^add/$', 'views.createWorkItem', {'reminder_id': None}),
    (r'^add/reminder_(?P<reminder_id>[0-9a-f\-]{36})/$','views.createWorkItem'),
    
    (r'^view/$', 'views.viewWork'),
    (r'^view/today/$', 'views.viewWork', {'datemin': datetime.date.today(), 'datemax': datetime.date.today()}),
    (r'^view/'+DATERANGE1+'/$', 'views.viewWork'),
    (r'^view/'+DATERANGE2+'/$', 'views.viewWork'),
    (r'^view/'+USERNAME+'/$', 'views.viewWork'),
    (r'^view/'+USERNAME+'/today/$', 'views.viewWork', {'datemin': datetime.date.today(), 'datemax': datetime.date.today()}),
    (r'^view/'+USERNAME+'/'+DATERANGE1+'/$', 'views.viewWork'),
    (r'^view/'+USERNAME+'/'+DATERANGE2+'/$', 'views.viewWork'),
)
