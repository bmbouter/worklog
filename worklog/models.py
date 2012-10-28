from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User

import worklog.admin_filter

class BiweeklyEmployee(models.Model):
    user = models.ForeignKey(User)
    univ_id = models.CharField(max_length=9, verbose_name='University ID')
    project_num = models.CharField(max_length=255, blank=True, verbose_name='Project #')
    obj_code = models.CharField(max_length=255, blank=True, verbose_name='Obj Code')
    hourly_pay = models.DecimalField(max_digits=5, decimal_places=2)

    def get_timesheet_name(self):
        return '%s, %s' % (self.user.last_name, self.user.first_name,)

    def __unicode__(self):
        return '%s' % self.user.get_full_name()

class Holiday(models.Model):
    description = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()

    def __unicode__(self):
        return '%s' % (self.description,)

class WorkPeriod(models.Model):
    payroll_id = models.CharField(max_length=8)
    start_date = models.DateField()
    end_date = models.DateField()
    due_date = models.DateField()
    pay_day = models.DateField()

    def __unicode__(self):
        return '%s' % (self.payroll_id,)

class Job(models.Model):
    name = models.CharField(max_length=256)
    # end_date is inclusive, so the duration of a Job is end_date-start_date + 1 day
    # if end_date==None, the Job is still open
    open_date = models.DateField()
    close_date = models.DateField(null=True, blank=True)
    do_not_invoice = models.BooleanField(default=False)
    users = models.ManyToManyField(User, null=True, blank=True)
    available_all_users = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name
    
    @staticmethod
    def get_jobs_open_on(date):
        return Job.objects.filter(open_date__lte=date).filter(Q(close_date__gte=date) | Q(close_date=None))
    
    def hasFunding(self):
        return len(self.funding.all()) != 0
    
    def hasWork(self):
        return len(WorkItem.objects.filter(job=self)) != 0

class BillingSchedule(models.Model):
    job = models.ForeignKey(Job, related_name='billing_schedule')
    date = models.DateField()

    def __unicode__(self):
        return 'Billing for %s' % self.job

class Funding(models.Model):
    job = models.ForeignKey(Job, related_name='funding')
    hours = models.IntegerField()
    date_available = models.DateField()

    def __unicode__(self):
        return 'Funding for %s' % self.job

class WorkItem(models.Model):
    user = models.ForeignKey(User)
    date = models.DateField()
    hours = models.IntegerField()
    text = models.TextField()
    job = models.ForeignKey(Job)
    invoiced = models.BooleanField(default=False)
    do_not_invoice = models.BooleanField(default=False)
    
    # see worklog.admin_filter
    date.year_month_filter = True
    user.user_filter = True
    invoiced.is_invoiced_filter = True    
    def __str__(self):
        return '%s on %s work %d hours on %s' % (self.user, self.date, self.hours, self.text)

    def save(self, *args, **kwargs):
        if(not self.job.available_all_users):
            if(not self.job.users.filter(id=self.user.id).exists()):
                return         
        super(WorkItem, self).save(*args, **kwargs) 





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

