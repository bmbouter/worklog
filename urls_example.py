from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'worklog/login.html'}),
    (r'^worklog/', include('worklog.urls')),
    (r'^$', include(admin.site.urls)),
)
