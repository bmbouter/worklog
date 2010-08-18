from django.db import models
from django.contrib.auth.models import User

class WorkItem(models.Model):
    user = models.ForeignKey(User)
    date = models.DateField()
    #date = models.DateField(auto_now_add=True)
    hours = models.IntegerField()
    text = models.TextField()
    class Admin:
        search_fields  = ('user', )
    def __str__(self):
        return '%s on %s work %d hours on %s' % (self.user, self.date, self.hours, self.text)


class WorkLogReminder(models.Model):
    reminder_id = models.CharField(max_length=36) # this is a uuid in string form
    user = models.ForeignKey(User)
    date = models.DateField()
    def __str__(self):
        return 'Reminder for %s on %s with id %s'%(self.user, self.date, self.id)

