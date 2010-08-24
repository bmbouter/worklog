from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User

import worklog.admin_filter


class Job(models.Model):
    name = models.CharField(max_length=256)
    #is_open = models.BooleanField(default=False)
    # end_date is inclusive, so the duration of a Job is end_date-start_date + 1 day
    # if end_date==None, the Job is still open
    open_date = models.DateField()
    close_date = models.DateField(null=True, blank=True)
    def __unicode__(self):
        return self.name
    @staticmethod
    def get_jobs_open_on(date):
        return Job.objects.filter(open_date__lte=date).filter(Q(close_date__gte=date) | Q(close_date=None))

class WorkItem(models.Model):
    user = models.ForeignKey(User)
    date = models.DateField()
    #date = models.DateField(auto_now_add=True)
    hours = models.IntegerField()
    text = models.TextField()
    job = models.ForeignKey(Job)

    date.year_month_filter = True
    user.user_filter = True
    #class Admin:
    #    search_fields  = ('user', )
    def __str__(self):
        return '%s on %s work %d hours on %s' % (self.user, self.date, self.hours, self.text)


class WorkLogReminder(models.Model):
    reminder_id = models.CharField(max_length=36) # this is a uuid in string form
    user = models.ForeignKey(User)
    date = models.DateField()
    submitted_jobs = models.ManyToManyField(Job) # prevent submitting for same job/date combination more than once
    def __str__(self):
        return 'Reminder for %s on %s with id %s'%(self.user, self.date, self.id)
    def get_available_jobs(self):
        jobs = Job.get_jobs_open_on(self.date)
        # exclude jobs already submitted with this reminder
        jobs = jobs.exclude(id__in=self.submitted_jobs.get_query_set())
        return jobs

