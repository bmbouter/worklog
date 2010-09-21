from celery.decorators import task, periodic_task
from celery.task.schedules import crontab
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse as urlreverse
import django.core.mail
from worklog.models import WorkItem, WorkLogReminder

import app_settings

import datetime
import uuid

email_msg = """\
Our records show you did not submit a work log today, %(date)s.  You may use the 
following URL to submit today's log, but you must do so before it expires on 
%(expiredate)s.

URL: %(url)s

"""

##submit_log_url = "http://opus-dev.cnl.ncsu.edu:7979/worklog/add/reminder_%s"

def compose_reminder_email(email_address, id, date):
    subj = "Remember to Submit Today's Worklog"
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
    

