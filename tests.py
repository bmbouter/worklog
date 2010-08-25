import unittest
import datetime
import uuid

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

from models import WorkItem, Job, WorkLogReminder
from forms import WorkItemForm
import tasks
import app_settings

class Worklog_TestCaseBase(TestCase):
    def setUp(self):
        today = datetime.date.today()
        last_week =     today - datetime.timedelta(days=7)
        last_2week =    today - datetime.timedelta(days=14)
        next_week =     today + datetime.timedelta(days=7)
        self.last_week = last_week
        
        job = Job.objects.create(name="Job_Today",open_date=today)
        job.save()
        job = Job.objects.create(name="Job_OneDay",open_date=today,close_date=today)
        job.save()
        job = Job.objects.create(name="Job_LastWeek",open_date=last_week)
        job.save()
        job = Job.objects.create(name="Job_LastWeek2",open_date=last_week, close_date=today)
        job.save()
        
        job = Job.objects.create(name="Job_Future",open_date=next_week)
        job.save()
        job = Job.objects.create(name="Job_Old",open_date=last_2week, close_date=last_week)
        job.save()
        
        self.user = User.objects.create_user(username="master", email="", password="password")
        
    def tearDown(self):
        # Clean up all test data.  This does not affect the 'real' database, 
        # only the test database
        Job.objects.all().delete()
        WorkItem.objects.all().delete()
        WorkLogReminder.objects.all().delete()
        # Delete all test users.
        self.user.delete()

class CreateWorkItem_TestCase(Worklog_TestCaseBase):
        
    def test_basic_get(self):
        #c = Client()
        self.client.login(username='master', password='password')
        response = self.client.get('/worklog/add/')
        self.assertEquals(response.context['reminder_id'],None)
        
        qs = response.context['form'].fields["job"].queryset
        
        self.assertEquals(qs.count(),4)
        names = list(job.name for job in qs)
        self.assertTrue("Job_Today" in names)
        self.assertTrue("Job_OneDay" in names)
        self.assertTrue("Job_LastWeek" in names)
        self.assertTrue("Job_LastWeek2" in names)
        
        self.client.logout()
        
    def test_basic_submitAndExit(self):
        self.client.login(username='master', password='password')
        
        job = Job.objects.filter(name='Job_Today')[0]
        data = {'submit_and_exit':'','hours':'2', 'text':'description', 'job':job.pk}
        response = self.client.post('/worklog/add/', data)
        
        self.assertRedirects(response, '/worklog/view/master/today/')
        
        items = WorkItem.objects.all()
        self.assertEquals(items.count(),1)
        
        item = items[0]
        self.assertEquals(item.date,datetime.date.today())
        self.assertEquals(item.hours,2)
        self.assertEquals(item.job,job)
        
        self.client.logout()
        
    def test_basic_submitAndAddAnother(self):
        self.client.login(username='master', password='password')
        
        job = Job.objects.filter(name='Job_Today')[0]
        data = {'submit_and_add_another':'','hours':'3', 'text':'description', 'job':job.pk}
        response = self.client.post('/worklog/add/', data)
        
        self.assertRedirects(response, '/worklog/add/')
        
        items = WorkItem.objects.all()
        self.assertEquals(items.count(),1)
        
        item = items[0]
        self.assertEquals(item.date,datetime.date.today())
        self.assertEquals(item.hours,3)
        self.assertEquals(item.job,job)
        
        self.client.logout()
        
    def test_reminder_get(self):
        uuidstr = '00001111000011110000111100001111'
        id = str(uuid.UUID(uuidstr))
        reminder = WorkLogReminder(reminder_id=id, user=self.user, date=self.last_week)
        reminder.save()
        
        self.client.login(username='master', password='password')
        response = self.client.get('/worklog/add/reminder_{0}/'.format(id))
        self.assertEquals(response.context['reminder_id'],id)
        
        qs = response.context['form'].fields["job"].queryset
        
        self.assertEquals(qs.count(),3)
        names = list(job.name for job in qs)
        self.assertTrue("Job_LastWeek" in names)
        self.assertTrue("Job_LastWeek2" in names)
        self.assertTrue("Job_Old" in names)
        
        self.client.logout()
        
    def test_reminder_submitAndExit(self):
        uuidstr = '00001111000011110000111100001111'
        id = str(uuid.UUID(uuidstr))
        reminder = WorkLogReminder(reminder_id=id, user=self.user, date=self.last_week)
        reminder.save()
        jobs = reminder.get_available_jobs()
        job = jobs[0]
        
        self.client.login(username='master', password='password')
        
        data = {'submit_and_exit':'','hours':'2', 'text':'description', 'job':job.pk}
        response = self.client.post('/worklog/add/reminder_{0}/'.format(id), data)
        
        self.assertRedirects(response, '/worklog/view/master/{0}/'.format(self.last_week))
        
        items = WorkItem.objects.all()
        self.assertEquals(items.count(),1)
        
        item = items[0]
        self.assertEquals(item.date, self.last_week)
        self.assertEquals(item.hours, 2)
        self.assertEquals(item.job, job)
        
        self.client.logout()
        
    def test_reminder_submitAndAddAnother(self):
        uuidstr = '00001111000011110000111100001111'
        id = str(uuid.UUID(uuidstr))
        reminder = WorkLogReminder(reminder_id=id, user=self.user, date=self.last_week)
        reminder.save()
        jobs = reminder.get_available_jobs()
        job = jobs[0]
        
        self.client.login(username='master', password='password')
        
        data = {'submit_and_add_another':'','hours':'4', 'text':'description', 'job':job.pk}
        response = self.client.post('/worklog/add/reminder_{0}/'.format(id), data)
        
        self.assertRedirects(response, '/worklog/add/reminder_{0}/'.format(id))
        
        items = WorkItem.objects.all()
        self.assertEquals(items.count(),1)
        
        item = items[0]
        self.assertEquals(item.date, self.last_week)
        self.assertEquals(item.hours, 4)
        self.assertEquals(item.job, job)
        
        self.client.logout()
        
        
class ClearExpiredReminders_TestCase(Worklog_TestCaseBase):
    def test_basic(self):
        # create some reminders
        uuidtpl = '{0:032d}'
        today = datetime.date.today()
        diffs = [0,1,
                 app_settings.EMAIL_REMINDERS_EXPIRE_AFTER-1, # 13
                 app_settings.EMAIL_REMINDERS_EXPIRE_AFTER,   # 14
                 app_settings.EMAIL_REMINDERS_EXPIRE_AFTER+1, # 15
                 -1,
                 -app_settings.EMAIL_REMINDERS_EXPIRE_AFTER+1, # -13
                 -app_settings.EMAIL_REMINDERS_EXPIRE_AFTER,   # -14
                 -app_settings.EMAIL_REMINDERS_EXPIRE_AFTER-1  # -15
                ]
        dates = list(today-datetime.timedelta(days=x) for x in diffs)
        for i,date in enumerate(dates):
            id = str(uuid.UUID(uuidtpl.format(i)))
            reminder = WorkLogReminder(reminder_id=id, user=self.user, date=date)
            reminder.save()
            
        rems = WorkLogReminder.objects.all()
        self.assertEquals(rems.count(),9)
        
        # clear the expired reminders
        tasks.clear_expired_reminder_records()
        
        # verify results
        rems = WorkLogReminder.objects.all()
        self.assertEquals(rems.count(),7)
        
        for rem in rems:
            self.assertTrue(rem.date > today-datetime.timedelta(days=app_settings.EMAIL_REMINDERS_EXPIRE_AFTER))

def suite():
    test_suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    test_suite.addTest(loader.loadTestsFromTestCase(CreateWorkItem_TestCase))
    test_suite.addTest(loader.loadTestsFromTestCase(ClearExpiredReminders_TestCase))
    return test_suite



