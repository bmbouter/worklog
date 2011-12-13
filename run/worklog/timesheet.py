import datetime as date
import ho.pisa as pisa
import cStringIO as StringIO

import django.core.mail
from django.core.mail import EmailMessage
from django.conf import settings
from django.http import HttpResponse
from django.template import Context
from django.template.loader import get_template

from worklog.models import WorkItem, BiweeklyEmployee, Holiday, WorkPeriod

days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
days_for_template = ['mon', 'tue', 'wed', 'thur', 'fri', 'sat', 'sun']

context = { }
template_name = 'worklog/timesheet.html'

# Generate the paysheet data for a given BiweeklyEmployee and WorkPeriod
# Returns a tuple of two lists where each list is a week in the work period
def get_hours(employee, work_period):
    holidays = Holiday.objects.filter(start_date__gte=work_period.start_date, \
        end_date__lte=work_period.end_date)
    work_items = WorkItem.objects.filter(user=employee.user, \
        date__range=(work_period.start_date, work_period.end_date))

    first_week = get_weekly_hours(work_period.start_date, \
        work_period.start_date + date.timedelta(days=7), work_items, holidays)
    second_week = get_weekly_hours(work_period.end_date - date.timedelta(days=6), \
        work_period.end_date + date.timedelta(days=1), work_items, holidays) # Have to add one extra day
                                                                             # for the end date to work

    return (first_week, second_week,)

# Get the hours worked in a week
# Returns a list of 7 tuples
# Each tuple is composed of a date and hours worked on that date
def get_weekly_hours(start_date, end_date, work_items, holidays):
    week = []
    current_date = start_date
    days = (end_date - start_date).days

    for day in range(days):
        daily_hours = 0
        daily_work = work_items.filter(date=current_date)
        
        if holidays.filter(start_date__lte=current_date, end_date__gte=current_date).count() == 0:
            for work in daily_work:
                daily_hours += work.hours
        
        week.append((current_date, daily_hours,))
    
        current_date += date.timedelta(days=1)
    
    return week

def set_timesheet_weeks(weeks):
    total_hours = 0

    for week in weeks:
        week_total_hours = 0

        for day in week:
            day_str = days_for_template[day[0].weekday()]
            hours = day[1]
            week_total_hours += hours

            week_str = '%sweek%d' % (day_str, (weeks.index(week) + 1),)
            context[week_str] = '%s/%s' % (day[0].month, day[0].day)
            context['%s_daily' % week_str] = hours

            if hours != 0:
                start_hour = '8:00a'
                end_hour = '%s:00p' % (8 + hours - 12) if 8 + hours > 12 else '%s:00a' % (8 + hours)

                context['%s_start' % week_str] = start_hour
                context['%s_end' % week_str] = end_hour
        
        context['week%d_total' % (weeks.index(week) + 1)] = week_total_hours
        total_hours += week_total_hours

    context['total'] = total_hours

def set_header(employee, work_period):
    d_format = '%m/%d/%y'

    context['name'] = '%s' % employee.get_timesheet_name()
    context['id_num'] = '%s' % employee.univ_id
    context['work_beginning'] = '%s' % work_period.start_date.strftime(d_format)
    context['work_ending'] = '%s' % work_period.end_date.strftime(d_format)
    context['prid'] = '%s' % work_period.payroll_id
    context['dept'] = '%s' % 'CSC/8206' 
    context['due_date'] = '%s' % work_period.due_date.strftime(d_format)
    context['pay_day'] = '%s' % work_period.pay_day.strftime(d_format)

def set_footer(employee):
    context['project_num'] = employee.project_num

def run(workperiod_id):
    if WorkPeriod.objects.filter(pk=workperiod_id).count() > 0:
        work_period = WorkPeriod.objects.get(pk=workperiod_id)

        for employee in BiweeklyEmployee.objects.all():
            weeks = get_hours(employee, work_period)
            set_header(employee, work_period)
            set_timesheet_weeks(weeks)
            set_footer(employee)

            template = get_template(template_name)
            html = template.render(Context(context))
            result = StringIO.StringIO()

            pdf = pisa.pisaDocument(StringIO.StringIO(html.encode('ISO-8859-1')), dest=result)

            if not pdf.err:
                send_email(employee, result.getvalue())

                # Reset the global context
                global context
                context = { }

def send_email(employee, pdf):
    subject = 'Timesheet for %s' % employee
    recipients = []

    for admin in settings.ADMINS:
        recipients.append(admin[1])
    
    email = EmailMessage(
        subject,
        'Timesheet is attached',
        '',
        recipients,
        attachments = [('timesheet.pdf', pdf, 'application/pdf',)]
    )

    email.send()

# View to generate a PDF for a given employee and work period
def make_pdf(request, payroll_id, employee_id):
    if WorkPeriod.objects.filter(pk=payroll_id).count() > 0:
        employee = BiweeklyEmployee.objects.get(pk=employee_id)
        work_period = WorkPeriod.objects.get(pk=payroll_id)

        weeks = get_hours(employee, work_period)
        set_header(employee, work_period)
        set_timesheet_weeks(weeks)
        set_footer(employee)

        response = HttpResponse(mimetype='application/pdf')
        response['Content-Disposition'] = 'filename=timesheet.pdf'

        template = get_template(template_name)
        html = template.render(Context(context))
        result = StringIO.StringIO()

        pdf = pisa.pisaDocument(StringIO.StringIO(html.encode('ISO-8859-1')), dest=result)

        if not pdf.err:
            response.write(result.getvalue())

            # Reset the global context
            global context
            context = { }

            return response
        else:
            return HttpResponse('Error!')











