from django.db import models
from django.contrib.auth.models import User

class WorkItem(models.Model):
    user = models.ForeignKey(User)
    #date = models.DateField()
    date = models.DateField(auto_now_add=True)
    hours = models.IntegerField()
    text = models.TextField()
    class Admin:
        search_fields  = ('user', )
    def __str__(self):
        return '%s on %s work %d hours on %s' % (self.user, self.date, self.hours, self.text)
