import datetime

from django.conf.urls.defaults import *

urlpatterns = patterns('worklog',
    (r'^add$', 'views.createWorkItem'),
    #(r'^$', 'views.placeOrder'),
    #(r'^thanks$', 'views.thanks'),
    (r'^view$', 'views.viewWork'),
    (r'^view/today$', 'views.viewWork', {'date': datetime.date.today()}),
    (r'^view/(?P<date>(\d{4}-\d{2}-\d{2}){1})$', 'views.viewWork'),
    (r'^view/(?P<user>([a-zA-Z0-9+])+)/$', 'views.viewWork'),
    (r'^view/(?P<user>([^/-])+)/today$', 'views.viewWork', {'date': datetime.date.today()}),
    (r'^view/(?P<user>([^/-])+)/(?P<date>(\d{4}-\d{2}-\d{2}){1})', 'views.viewWork'),
    #(r'^orders/today$', 'views.viewOrders'),
    #(r'^orders/(?P<date>(\d{4}-\d{2}-\d{2}){1})$', 'views.viewOrders'),
)
