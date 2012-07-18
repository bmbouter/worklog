import datetime as date
import ho.pisa as pisa
import cStringIO as StringIO
import re

import django.core.mail
from django.core.mail import EmailMessage
from django.conf import settings
from django.http import HttpResponse
from django.template import Context
from django.template.loader import get_template
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404

from worklog.models import WorkItem, BiweeklyEmployee, Holiday, WorkPeriod

# Class representing a timesheet
class Timesheet:
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    days_for_template = ['mon', 'tue', 'wed', 'thur', 'fri', 'sat', 'sun']

    template_name = 'worklog/timesheet_template.html'

    def __init__(self, employee, workperiod):
        self.employee = employee
        self.work_period = workperiod
        self.context = { }
        self.pdf = None

    # Generate the paysheet data for a given BiweeklyEmployee and WorkPeriod
    # Returns a tuple of two lists where each list is a week in the work period
    def get_hours(self):
        holidays = Holiday.objects.filter(start_date__gte=self.work_period.start_date, \
            end_date__lte=self.work_period.end_date)
        work_items = WorkItem.objects.filter(user=self.employee.user, \
            date__range=(self.work_period.start_date, self.work_period.end_date))

        first_week = self.get_weekly_hours(self.work_period.start_date, \
            self.work_period.start_date + date.timedelta(days=7), work_items, holidays)
        second_week = self.get_weekly_hours(self.work_period.end_date - date.timedelta(days=6), \
            self.work_period.end_date + date.timedelta(days=1), work_items, holidays) # Have to add one extra day
                                                                                 # for the end date to work

        return (first_week, second_week,)

    # Get the hours worked in a week
    # Returns a list of 7 tuples
    # Each tuple is composed of a date and hours worked on that date
    def get_weekly_hours(self, start_date, end_date, work_items, holidays):
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

    def set_timesheet_weeks(self, weeks):
        total_hours = 0

        for week in weeks:
            week_total_hours = 0

            for day in week:
                day_str = self.days_for_template[day[0].weekday()]
                hours = day[1]
                week_total_hours += hours

                week_str = '%sweek%d' % (day_str, (weeks.index(week) + 1),)
                self.context[week_str] = '%s/%s' % (day[0].month, day[0].day)
                self.context['%s_daily' % week_str] = hours

                if hours != 0:
                    start_hour = '8:00a'
                    end_hour = '%s:00p' % (8 + hours - 12) if 8 + hours > 12 else '%s:00a' % (8 + hours)

                    self.context['%s_start' % week_str] = start_hour
                    self.context['%s_end' % week_str] = end_hour
            
            self.context['week%d_total' % (weeks.index(week) + 1)] = week_total_hours
            total_hours += week_total_hours

        self.context['total'] = total_hours

    def set_header(self):
        d_format = '%m/%d/%y'

        self.context['name'] = '%s' % self.employee.get_timesheet_name()
        self.context['id_num'] = '%s' % self.employee.univ_id
        self.context['work_beginning'] = '%s' % self.work_period.start_date.strftime(d_format)
        self.context['work_ending'] = '%s' % self.work_period.end_date.strftime(d_format)
        self.context['prid'] = '%s' % self.work_period.payroll_id
        self.context['dept'] = '%s' % 'CSC/8206' 
        self.context['due_date'] = '%s' % self.work_period.due_date.strftime(d_format)
        self.context['pay_day'] = '%s' % self.work_period.pay_day.strftime(d_format)

    def set_footer(self):
        self.context['project_num'] = self.employee.project_num
        self.context['obj_code'] = self.employee.obj_code
        self.context['hourly_pay'] = self.employee.hourly_pay

    def get_pdf(self):
        weeks = self.get_hours()
        self.set_header()
        self.set_timesheet_weeks(weeks)
        self.set_footer()

        template = get_template(self.template_name)
        html = template.render(Context(self.context))
        result = StringIO.StringIO()

        pdf = pisa.pisaDocument(StringIO.StringIO(html.encode('ISO-8859-1')), dest=result)

        if not pdf.err:
            self.pdf = result.getvalue()
            return result.getvalue()
        else:
            return None

    def send_email(self):
        subject = 'Timesheet for %s' % self.employee
        recipients = []

        for admin in settings.ADMINS:
            recipients.append(admin[1])
        
        email = EmailMessage(
            subject,
            'Timesheet is attached',
            '',
            recipients,
            attachments = [('timesheet.pdf', self.pdf, 'application/pdf',)]
        )

        email.send()

# View that displays a page of biweekly employees. Timesheets can be
# requested for individual or all employees
class TimesheetView(TemplateView):
    template_name = 'worklog/timesheet.html'

    def get_context_data(self, **kwargs):
        context = super(TimesheetView, self).get_context_data()

        context['employees'] = BiweeklyEmployee.objects.all()
        return context

    def get(self, request, *args, **kwargs):
        if 'date' in request.GET:
            regex = re.compile('\d{4}-\d{2}-\d{2}')

            if not regex.match(request.GET['date']):
                context = {'error': 'Please provide a valid date'}
                return super(TimesheetView, self).render_to_response(context)
            
            date = request.GET['date']
            
            context = self.get_context_data(**kwargs)
            context['date'] = date

            return super(TimesheetView, self).render_to_response(context)
        else:
            context = {'error': 'Please provide a valid date'}
            return super(TimesheetView, self).render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        due_date = date.datetime.strptime(request.POST['date'], '%Y-%m-%d').date()
        work_period = get_object_or_404(WorkPeriod, due_date=due_date)
        context = self.get_context_data(**kwargs)

        if 'all_employees' in request.POST:
            for employee in BiweeklyEmployee.objects.all():
                timesheet = Timesheet(employee, work_period)
                pdf = timesheet.get_pdf()
                
                if pdf is not None:
                    timesheet.send_email()
                else:
                    context['error'] = 'Please provide a valid date'
                    return super(TimesheetView, self).render_to_response(context)
            
            context['success'] = 'Emails with timesheets were sent'
        else:
            employee = BiweeklyEmployee.objects.get(pk=request.POST['employee_id'])
            timesheet = Timesheet(employee, work_period)
            
            pdf = timesheet.get_pdf()

            if pdf is not None:
                timesheet.send_email()
            else:
                context['error'] = 'Please provide a valid date'
                return super(TimesheetView, self).render_to_response(context)

            context['success'] = 'Email with timesheet was sent'
        
        context['date'] = request.POST['date']

        return super(TimesheetView, self).render_to_response(context)


# View to generate a PDF for a given employee and work period
def make_pdf(request, payroll_id, employee_id):
    if WorkPeriod.objects.filter(pk=payroll_id).count() > 0:
        employee = BiweeklyEmployee.objects.get(pk=employee_id)
        work_period = WorkPeriod.objects.get(pk=payroll_id)

        timesheet = Timesheet(employee, work_period)

        pdf = timesheet.get_pdf()

        response = HttpResponse(mimetype='application/pdf')
        response['Content-Disposition'] = 'filename=timesheet.pdf'

        if pdf is not None:
            response.write(pdf)
            return response
        else:
            return HttpResponse('Error!')
