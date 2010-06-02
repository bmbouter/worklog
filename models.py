from django.db import models
from django.contrib.auth.models import User

class WorkItem(models.Model):
    user = models.ForeignKey(User)
    date = models.DateField(auto_now_add=True)
    hours = models.IntegerField()
    text = models.TextField()
