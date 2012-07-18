from django.db import models
from django.contrib.admin import SimpleListFilter
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _

from django.contrib.auth.models import User

import datetime
import operator

# used in YearMonthFilterSpec.__init__
def create_yearmonth_link(d,fieldname):
    """d = a datetime.date object """
    title = smart_unicode(d.strftime('%Y %B'))
    param_dict = { 
            '%s__year' % fieldname: str(d.year), 
            '%s__month' % fieldname: str(d.month), 
            }
    return title,param_dict

class YearMonthFilterSpec(SimpleListFilter):
    def __init__(self, f, request, params, model, *args, **kwargs):
        super(YearMonthFilterSpec,self).__init__(f,request,params,model,*args,**kwargs)
        
        self.field_generic = '%s__' % self.field.name
        self.date_params = dict([(k, v) for k, v in params.items() if k.startswith(self.field_generic)])
        
        values_list = model.objects.values_list(f.name, flat=True)
        unique_dates = list(set(
            val.replace(day=1) for val in values_list if isinstance(val, datetime.date)
            ))
        # using reverse=True results in most recent date being listed first
        unique_dates.sort(reverse=True)
        self.links = list(create_yearmonth_link(d,self.field.name) for d in unique_dates)
        self.links.insert(0,(_('All'),{}))
        

    def choices(self, cl):
        for title, param_dict in self.links:
            yield {'selected': self.date_params == param_dict,
                   'query_string': cl.get_query_string(param_dict, [self.field_generic]),
                   'display': title } 

    def title(self):
        return _('year and month')


class UserFilterSpec(SimpleListFilter):
    def __init__(self, f, request, params, model, *args, **kwargs):
        super(UserFilterSpec, self).__init__(f, request, params, model, *args, **kwargs)

        values_list = model.objects.values_list(f.name, flat=True)
        
        self.lookup_choices = list((x.pk,x.username) for x in User.objects.all())
        self.lookup_choices.sort(key=operator.itemgetter(0))

    def choices(self, cl):
        yield {'selected': self.lookup_val is None,
               'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
               'display': _('All')}
        for id,name in self.lookup_choices:
            yield {'selected': smart_unicode(id) == self.lookup_val,
                   'query_string': cl.get_query_string({self.lookup_kwarg: id}),
                   'display': smart_unicode(name)}

class IsInvoicedFilterSpec(SimpleListFilter):
    """
    Adds filtering by future and previous values in the admin
    filter sidebar. Set the is_live_filter filter in the model field attribute
    'is\_live\_filter'.    my\_model\_field.is\_live\_filter = True
    """

    def __init__(self, f, request, params, model, *args, **kwargs):
        super(IsInvoicedFilterSpec, self).__init__(f, request, params, model, *args, **kwargs)
        self.links = (
            (_('Any'), {}),
            (_('Not Invoiced'), {'%s__exact' % self.field.name: "0",}),
            (_('Invoiced'), {'%s__exact' % self.field.name: "1",}),
        )

    def title(self):
        return "Invoiced"

