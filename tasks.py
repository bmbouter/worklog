from celery.decorators import task, periodic_task
from celery.task.schedules import crontab
from django.contrib.auth.models import User
import django.core.mail
from worklog.models import WorkItem, WorkLogReminder

import datetime
import uuid

#@task
#def add(x,y):
#    return x+y

email_msg = """\
Our records show you did not submit a work log today.  You may use the 
following URL to submit your log for today, even at a later date.

<a href="%(url)s">Submit a work log</a>

URL: %(url)s

"""

submit_log_url = "http://opus-dev.cnl.ncsu.edu:7979/worklog/add/reminder_%s"

def compose_reminder_email(email_address, id):
    subj = "Remember to Submit Today's Worklog"
    msg = email_msg%{'url': submit_log_url%id}
    from_email = ""
    recipients = [email_address]

    return (subj, msg, from_email, recipients)

def save_reminder_record(user,id, date):
    reminder = WorkLogReminder(reminder_id=id, user=user, date=date)
    reminder.save()

# periodic task: M-F at 6:00pm
@periodic_task(run_every=crontab(hour=18, minute=0, day_of_week=[1,2,3,4,5]))
def send_reminder_emails():
    datatuples = ()
    date = datetime.date.today()-datetime.timedelta(days=1)
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

