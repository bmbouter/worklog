from celery.decorators import task, periodic_task
from celery.task.schedules import crontab
from django.contrib.auth.models import User
import django.core.mail
from worklog.models import WorkItem, WorkLogReminder

import app_settings

import datetime
import uuid

#@task
#def add(x,y):
#    return x+y

email_msg = """\
Our records show you did not submit a work log today.  You may use the 
following URL to submit today's log, but you must do so before it expires on 
%(expiredate)s.

URL: %(url)s

"""

submit_log_url = "http://opus-dev.cnl.ncsu.edu:7979/worklog/add/reminder_%s"

def compose_reminder_email(email_address, id):
    subj = "Remember to Submit Today's Worklog"
    expire_days = app_settings.EMAIL_REMINDERS_EXPIRE_AFTER
    expiredate = datetime.date.today() + datetime.timedelta(days=expire_days)
    msg = email_msg%{'url': submit_log_url%id, 'expiredate': str(expiredate)}
    from_email = ""
    recipients = [email_address]

    return (subj, msg, from_email, recipients)

def save_reminder_record(user,id, date):
    reminder = WorkLogReminder(reminder_id=id, user=user, date=date)
    reminder.save()
    
    
send_hour = app_settings.SEND_REMINDERS_HOUR
send_days = app_settings.SEND_REMINDERS_DAYSOFWEEK

# periodic task: M-F at 6:00pm
@periodic_task(run_every=crontab(hour=send_hour, minute=0, day_of_week=send_days))
def send_reminder_emails():
    datatuples = ()
    #date = datetime.date.today()-datetime.timedelta(days=1)
    date = datetime.date.today()
    for user in User.objects.all():
    #for user in User.objects.filter(username='dpwhite2'):
        items = WorkItem.objects.filter(user=user.pk,date=date)
        if not items:
        #if items:
            # no work item today...
            id = str(uuid.uuid4())
            save_reminder_record(user,id,date)
            et = compose_reminder_email(user.email, id)
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
        

def test_send_reminder_email(date=datetime.date.today()):
    # For debugging purposes: sends a reminder email
    user = User.objects.filter(username='dpwhite2')[0]
    
    id = str(uuid.uuid4())
    save_reminder_record(user,id,date)
    et = compose_reminder_email(user.email, id)
    subj, msg, from_email, recipients = et
    
    django.core.mail.send_mail(subj, msg, from_email, recipients, fail_silently=False)
    

