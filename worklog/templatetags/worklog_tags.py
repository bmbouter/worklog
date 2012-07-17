from django import template
register = template.Library() 


# The following was taken from: 
#       django/contrib/admin/templatetags/admin_list.py
# This is nearly identical to the cited code.  This is used by our overridden 
# admin template.
def workitem_admin_actions(context):
    """
    Track the number of times the action field has been rendered on the page,
    so we know which value to use.
    """    
    context['action_index'] = context.get('action_index', -1) + 1    
    return context
    
workitem_admin_actions = register.inclusion_tag("admin/worklog/workitem/actions.html", takes_context=True)(workitem_admin_actions)

