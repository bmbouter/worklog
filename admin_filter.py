from django.db import models
from django.contrib.admin.filterspecs import FilterSpec, ChoicesFilterSpec
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _

from django.contrib.auth.models import User

import datetime
import operator

def create_yearmonth_link(d,fieldname):
    """d = a datetime.date object """
    title = smart_unicode(d.strftime('%Y %B'))
    param_dict = { 
            '%s__year' % fieldname: str(d.year), 
            '%s__month' % fieldname: str(d.month), 
            }
    return title,param_dict

class YearMonthFilterSpec(FilterSpec):
    def __init__(self, f, request, params, model, model_admin):
        super(YearMonthFilterSpec,self).__init__(f,request,params,model,model_admin)
        
        self.field_generic = '%s__' % self.field.name
        self.date_params = dict([(k, v) for k, v in params.items() if k.startswith(self.field_generic)])
        #self.lookup_kwarg = '%s__year_month'%f.name
        #self.lookup_val = request.GET.get(self.lookup_kwarg, None)
        
        #values_list = model.objects.values_list(f.name, flat=True)
        #self.lookup_choices = list(set(
        #    val.replace(day=1) for val in values_list if isinstance(val, datetime.date)
        #    ))
        #self.lookup_choices.sort(reverse=True)
        
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


class UserFilterSpec(ChoicesFilterSpec):
    def __init__(self, f, request, params, model, model_admin):
        super(UserFilterSpec, self).__init__(f, request, params, model, model_admin)
        #self.lookup_kwarg = '%s__exact' % f.name
        #self.lookup_val = request.GET.get(self.lookup_kwarg, None)

        values_list = model.objects.values_list(f.name, flat=True)
        
        self.lookup_choices = list((x.pk,x.username) for x in User.objects.all())
        #self.lookup_choices = list(set((val,Users.objects.filter for val in values_list if val))
        self.lookup_choices.sort(key=operator.itemgetter(0))

    def choices(self, cl):
        yield {'selected': self.lookup_val is None,
               'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
               'display': _('All')}
        for id,name in self.lookup_choices:
            yield {'selected': smart_unicode(id) == self.lookup_val,
                   'query_string': cl.get_query_string({self.lookup_kwarg: id}),
                   'display': smart_unicode(name)}



FilterSpec.filter_specs.insert(0, (lambda f: getattr(f, 'year_month_filter', False), YearMonthFilterSpec))
FilterSpec.filter_specs.insert(0, (lambda f: getattr(f, 'user_filter', False), UserFilterSpec))


