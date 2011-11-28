from django.conf import settings
from celery.decorators import task, periodic_task
from celery.task.schedules import crontab
from celery.registry import TaskRegistry
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse as urlreverse
import django.core.mail

from worklog import timesheet
from worklog.models import WorkItem, WorkLogReminder, Job, WorkPeriod

import app_settings

import datetime, calendar
import uuid

email_msg = """\
Our records show you did not submit a work log today, %(date)s.  You may use the 
following URL to submit today's log, but you must do so before it expires on 
%(expiredate)s.

URL: %(url)s

"""

#registry = TaskRegistry()

##submit_log_url = "http://opus-dev.cnl.ncsu.edu:7979/worklog/add/reminder_%s"

# Generate at 2 AM daily and check if the work period is over
@periodic_task(run_every=crontab(hour=2, minute=0, day_of_week=[0,1,2,3,4,5,6]))
def generate_timesheets():
    if WorkPeriod.objects.filter(due_date=datetime.date.today()).count() > 0:
        timesheet.generate_email(WorkPeriod.objects.get(due_date=datetime.date.today()).pk)

# Generate at 2 AM daily during the week
@periodic_task(run_every=crontab(hour=2, minute=0, day_of_week=[0,1,2,3,4,5,6]))
def generate_invoice():
    cal = calendar.Calendar(0)
    billable_jobs = Job.objects.filter(billing_schedule__date__lte=datetime.date.today()).distinct()
    send_mail = True
    
    # continue only if we can bill jobs
    if billable_jobs:
        job_work_items = []
        
        # loop through all the jobs
        for job in billable_jobs:
            work_items = WorkItem.objects.filter(job=job, invoiced=False).exclude(do_not_invoice=True).distinct().order_by('date')
            
            # continue only if we have work items
            if work_items:
                # start at the first work item date
                first_date = work_items[0].date
                last_work_item = work_items.order_by('-date')[0]
                
                # end at the last work item or today (billing date)
                if last_work_item.date < datetime.date.today():
                    end_date = last_work_item.date
                else:
                    end_date = datetime.date.today()
                    
                days = (end_date - first_date).days
                
                week_of_str = '%s/%s/%s'
                job_msg_str = '\n%s (%s)'
                
                total_hours = 0
                weekly_work_items = []
                
                # continue to calculate hours until we reach the end date
                while first_date < end_date:
                    # used to grab weeks in a month; this will stagger the starting weeks of certain months
                    month = calendar.monthcalendar(first_date.year, first_date.month)
                    
                    for week in month:
                        weekly_hours = 0
                        work_item_msgs = []
                        days = [day for day in week if day != 0] # we need the first day of the month
                        date = datetime.date(first_date.year, first_date.month, days[0])
                        
                        # if its the first day of the week, set the week of string
                        if date.weekday == 0 or date.day == days[0]:
                            week_of = week_of_str % (date.month, date.day, date.year)
                            work_item_msgs.append(week_of)
                        
                        # calculate the work for each day
                        for day in week:
                            if day != 0:
                                items = work_items.filter(date=date)
                                
                                for item in items:
                                    total_hours += item.hours
                                    weekly_hours += item.hours
                                    work_item_msg = '\t\t%s hours, %s on %s' % (item.hours, item.text, date)
                                    work_item_msgs.append(work_item_msg)
                                   
                                date += datetime.timedelta(days=1)
                        
                        # adjust the first date for loop check and add the weekly hours to the week
                        first_date = date
                        work_item_msgs[0] += ' (%s)' % weekly_hours
                        weekly_work_items.append(work_item_msgs)
                        
                job_work_items.append((job_msg_str % (job.name, total_hours), weekly_work_items,));
            else:
                send_mail = False
    else:
        send_mail = False
    
    if send_mail:
        sub = 'Invoice'
        date_str = '\n\tDate: Week of %s\n'
        email_msgs = []
        
        # a list of tuples (job, work items in a month)
        for item in job_work_items:
            job_msgs = []
            job = item[0]
            entries = item[1]
            
            # a list where the first entry is the week and the rest are work items
            for entry in entries:
                if len(entry) > 1:
                    date = date_str % entry[0]
                    work_item_msgs = []
                    
                    # loop through the work items
                    for work in entry[1:]:
                        work_item_msgs.append(work)
                    
                    job_msgs.append(date + ('\n').join(work_item_msgs))
            
            email_msgs.append(job + ('').join(job_msgs))
        
        msg = ('\n').join(email_msgs)
        
        msg += '\n\nReport tools: %s' % app_settings.WORKLOG_EMAIL_LINK_URLBASE + urlreverse('report_url')
        
        recipients = []
        
        for admin in settings.ADMINS:
            recipients.append(admin[1])

        django.core.mail.send_mail(sub, msg, '', recipients)

def compose_reminder_email(email_address, id, date):
    subj = "Remember to Submit Today's Worklog (%s)"%str(date)
    expire_days =   app_settings.EMAIL_REMINDERS_EXPIRE_AFTER
    expiredate =    date + datetime.timedelta(days=expire_days)
    url =           create_reminder_url(id)
    msg = email_msg%{'url': url, 'expiredate': str(expiredate), 'date': str(date)}
    from_email = ""
    recipients = [email_address]

    return (subj, msg, from_email, recipients)
    
def create_reminder_url(id): 
    path = urlreverse('worklog-reminder-view', kwargs={'reminder_id':id}, current_app='worklog')
    return app_settings.WORKLOG_EMAIL_LINK_URLBASE+path

def save_reminder_record(user,id, date):
    reminder = WorkLogReminder(reminder_id=id, user=user, date=date)
    reminder.save()
    
    
send_hour = app_settings.SEND_REMINDERS_HOUR
send_days = app_settings.SEND_REMINDERS_DAYSOFWEEK

# periodic task -- by default: M-F at 6:00pm
@periodic_task(run_every=crontab(hour=send_hour, minute=0, day_of_week=send_days))
def send_reminder_emails():
    datatuples = ()  # one tuple for each email to send... contains subj, msg, recipients, etc...
    date = datetime.date.today()
    for user in User.objects.all():
        if not user.email: continue
        # get all workitems for 'user' that were submitted today
        items = WorkItem.objects.filter(user=user.pk,date=date)
        if not items:
            # no work item today...
            id = str(uuid.uuid4())
            save_reminder_record(user,id,date)
            et = compose_reminder_email(user.email, id, date)
            datatuples = datatuples + (et,)
    if datatuples:
        django.core.mail.send_mass_mail(datatuples, fail_silently=False)
        
    
clear_hour = app_settings.CLEAR_REMINDERS_HOUR
clear_days = app_settings.CLEAR_REMINDERS_DAYSOFWEEK
        
@periodic_task(run_every=crontab(hour=clear_hour, minute=0, day_of_week=clear_days))
def clear_expired_reminder_records():
    reminders_expire_days = app_settings.EMAIL_REMINDERS_EXPIRE_AFTER
    olddate = datetime.date.today() - datetime.timedelta(days=reminders_expire_days)
    oldrecs = WorkLogReminder.objects.filter(date__lte=olddate)
    oldrecs.delete()


def test_send_reminder_email(username, date=datetime.date.today()):
    # For debugging purposes: sends a reminder email
    user = User.objects.filter(username=username)[0]
    
    id = str(uuid.uuid4())
    save_reminder_record(user,id,date)
    et = compose_reminder_email(user.email, id, date)
    subj, msg, from_email, recipients = et
    
    django.core.mail.send_mail(subj, msg, from_email, recipients, fail_silently=False)


#registry.register(generate_invoice)