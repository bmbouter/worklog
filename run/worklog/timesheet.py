import datetime as date

from django.conf import settings
import django.core.mail

from worklog.models import WorkItem, BiweeklyEmployee, Holiday, WorkPeriod

days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

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

# Using a tuple of two weeks, return a formatted timesheet
def get_timesheet_weeks(weeks):
    weeks_str = ''
    total_hours = 0

    for week in weeks:
        week_list = []
        week_total_hours = 0

        for day in week:
            day_str = days[day[0].weekday()]
            hours = day[1]
            week_total_hours += hours
            
            if hours != 0:
                start_hour = '8:00a'
                end_hour = '%s:00p' % (8 + hours - 12) if 8 + hours > 12 else '%s:00a' % (8 + hours)
                
                week_list.append('%s (%s/%s)\nIn: %s\nOut: %s' % (day_str, day[0].month, day[0].day, \
                    start_hour, end_hour,))

        total_hours += week_total_hours
        weeks_str += '\n\n'.join(week_list) + '\n\nTotal hours worked this week: %s\n\n' % week_total_hours
    
    weeks_str += 'Total hours worked: %s' % total_hours

    return weeks_str

# Return the header of the document containing employee information
def get_header(employee, work_period):
    d_format = '%m/%d/%y'

    name = 'Name: %s' % employee.get_timesheet_name()
    id_num = 'ID#: %s' % employee.univ_id
    work_beginning = 'Work Period Beginning: %s' % work_period.start_date.strftime(d_format)
    work_ending = 'Work Period Ending: %s' % work_period.end_date.strftime(d_format)
    prid = 'PRID: %s' % work_period.payroll_id
    dept = 'Dept./Box#: %s' % 'CSC/8206' 
    due_date = 'Time Sheet Due Date: %s' % work_period.due_date.strftime(d_format)
    pay_day = 'Pay Day: %s' % work_period.pay_day.strftime(d_format)

    msg = '%s\t%s\t%s\t\t%s\n' % (name, work_beginning, prid, due_date)
    msg += '%s\t\t%s\t%s\t%s\n' % (id_num, work_ending, dept, pay_day)

    return msg

# Generates the timesheet for all biweekly employees in the system
def run():
    if WorkPeriod.objects.filter(end_date=date.date.today()).count() > 0:
        msg = []

        for employee in BiweeklyEmployee.objects.all():
            for work_period in WorkPeriod.objects.filter(end_date=date.date.today()):
                header = get_header(employee, work_period)
                weeks = get_timesheet_weeks(get_hours(employee, work_period))

                msg.append('\n'.join([header, weeks, '------------------------\n']))
        
        return '\n'.join(msg)
    else:
        return 'There is no work to report'

# Sends the email to the admins listed in settings
def generate_email():
    sub = 'Bi-weekly Timesheets'
    recipients = []
    msg = run()

    for admin in settings.ADMINS:
        recipients.append(admin[1])

    django.core.mail.send_mail(sub, msg, '', recipients)














