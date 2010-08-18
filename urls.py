import datetime

from django.conf.urls.defaults import *

urlpatterns = patterns('worklog',
    (r'^add/$', 'views.createWorkItem'),
    (r'^add/reminder_(?P<reminder_id>[0-9a-f\-]{36})/$','views.createWorkItemReminder'),
    #(r'^$', 'views.placeOrder'),
    #(r'^thanks$', 'views.thanks'),
    (r'^view/$', 'views.viewWork'),
    (r'^view/today/$', 'views.viewWork', {'date': datetime.date.today()}),
    (r'^view/(?P<date>(\d{4}-\d{2}-\d{2}){1})/$', 'views.viewWork'),
    (r'^view/(?P<username>([a-zA-Z0-9])+)/$', 'views.viewWork'),
    (r'^view/(?P<username>([a-zA-Z0-9])+)/today/$', 'views.viewWork', {'date': datetime.date.today()}),
    (r'^view/(?P<username>([a-zA-Z0-9])+)/(?P<date>(\d{4}-\d{2}-\d{2}){1})/$', 'views.viewWork'),
    #(r'^orders/today$', 'views.viewOrders'),
    #(r'^orders/(?P<date>(\d{4}-\d{2}-\d{2}){1})$', 'views.viewOrders'),
)
