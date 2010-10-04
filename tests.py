import unittest
import datetime
import calendar
import uuid

from django.test import TestCase
from django.core import mail # for testing email functionality
from django.test.client import Client
from django.contrib.auth.models import User

from models import WorkItem, Job, WorkLogReminder
from forms import WorkItemForm
import tasks
import app_settings

class UserLogin_Context(object):
    def __init__(self, client, username, password):
        self.client = client
        self.username = username
        self.password = password
    def __enter__(self):
        self.client.login(username=self.username, password=self.password)
    def __exit__(self, type, value, traceback):
        self.client.logout()

class Worklog_TestCaseBase(TestCase):
    def setUp(self):
        today = datetime.date.today()
        self.today = today
        last_week =     today - datetime.timedelta(days=7)
        last_2week =    today - datetime.timedelta(days=14)
        next_week =     today + datetime.timedelta(days=7)
        self.last_week = last_week
        self.next_week = next_week
        self.yesterday =    self.today - datetime.timedelta(days=1)
        self.tomorrow =     self.today + datetime.timedelta(days=1)
        
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
        
        self.user = User.objects.create_user(username="master", email="master@example.com", password="password")
        self.user2 = User.objects.create_user(username="user2", email="user2@example.com", password="password")
        
    def tearDown(self):
        # Clean up all test data.  This does not affect the 'real' database, 
        # only the test database
        Job.objects.all().delete()
        WorkItem.objects.all().delete()
        WorkLogReminder.objects.all().delete()
        # Delete all test users.
        self.user.delete()
        self.user2.delete()
        
    # for use in 'with' statements
    def scoped_login(self, username, password):
        return UserLogin_Context(self.client, username, password)
        
def get_month_end(d):
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])

class CreateWorkItem_TestCase(Worklog_TestCaseBase):
        
    def test_basic_get(self):
        with self.scoped_login('master', 'password'):
            response = self.client.get('/worklog/add/')
            self.assertEquals(response.context['reminder_id'],None)
            
            qs = response.context['form'].fields["job"].queryset
            
            self.assertEquals(qs.count(),4)
            names = list(job.name for job in qs)
            self.assertTrue("Job_Today" in names)
            self.assertTrue("Job_OneDay" in names)
            self.assertTrue("Job_LastWeek" in names)
            self.assertTrue("Job_LastWeek2" in names)
            
            self.assertEquals(len(response.context['items']),0)
        
    def test_basic_submitAndExit(self):
        with self.scoped_login(username='master', password='password'):
        
            job = Job.objects.filter(name='Job_Today')[0]
            data = {'submit_and_exit':'','hours':'2', 'text':'description', 'job':job.pk}
            response = self.client.post('/worklog/add/', data)
            
            #datemin = self.today.replace(day=1)
            #datemax = get_month_end(self.today)
            
            redirurl = '/worklog/view/{0}/today/'.format(self.user.username)
            self.assertRedirects(response, redirurl)
            
            items = WorkItem.objects.all()
            self.assertEquals(items.count(),1)
            
            item = items[0]
            self.assertEquals(item.date,datetime.date.today())
            self.assertEquals(item.hours,2)
            self.assertEquals(item.job,job)
        
    def test_basic_submitAndAddAnother(self):
        with self.scoped_login(username='master', password='password'):
        
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
        
    def test_reminder_get(self):
        uuidstr = '00001111000011110000111100001111'
        id = str(uuid.UUID(uuidstr))
        reminder = WorkLogReminder(reminder_id=id, user=self.user, date=self.last_week)
        reminder.save()
        
        with self.scoped_login(username='master', password='password'):
            response = self.client.get('/worklog/add/reminder_{0}/'.format(id))
            
            self.assertEquals(response.context['reminder_id'],id)
            
            qs = response.context['form'].fields["job"].queryset
            
            self.assertEquals(qs.count(),3)
            names = list(job.name for job in qs)
            self.assertTrue("Job_LastWeek" in names)
            self.assertTrue("Job_LastWeek2" in names)
            self.assertTrue("Job_Old" in names)
            
    
    def test_badReminder(self):
        uuidstr = '00001111000011110000111100001111'
        id = str(uuid.UUID(uuidstr))
        # NOTE: not adding reminder
        
        with self.scoped_login(username='master', password='password'):
            response = self.client.get('/worklog/add/reminder_{0}/'.format(id))
            
            self.assertTrue(response.has_header('Worklog-UnableToCreateItem'))
    
    def test_badUser(self):
        uuidstr = '00001111000011110000111100001111'
        id = str(uuid.UUID(uuidstr))
        reminder = WorkLogReminder(reminder_id=id, user=self.user2, date=self.last_week)
        reminder.save()
        
        # NOTE: login user does not match user associated with the reminder
        with self.scoped_login(username='master', password='password'):
            response = self.client.get('/worklog/add/reminder_{0}/'.format(id))
            
            self.assertTrue(response.has_header('Worklog-UnableToCreateItem'))
    
        
    def test_reminder_submitAndExit(self):
        uuidstr = '00001111000011110000111100001111'
        id = str(uuid.UUID(uuidstr))
        reminder = WorkLogReminder(reminder_id=id, user=self.user, date=self.last_week)
        reminder.save()
        jobs = reminder.get_available_jobs()
        job = jobs[0]
        
        with self.scoped_login(username='master', password='password'):
        
            data = {'submit_and_exit':'','hours':'2', 'text':'description', 'job':job.pk}
            response = self.client.post('/worklog/add/reminder_{0}/'.format(id), data)
            
            #datemin = self.last_week.replace(day=1)
            #datemax = get_month_end(self.last_week)
            
            redirurl = '/worklog/view/{0}/{1}_{1}/'.format(self.user.username,self.last_week)
            self.assertRedirects(response, redirurl)
            
            items = WorkItem.objects.all()
            self.assertEquals(items.count(),1)
            
            item = items[0]
            self.assertEquals(item.date, self.last_week)
            self.assertEquals(item.hours, 2)
            self.assertEquals(item.job, job)
        
    def test_reminder_submitAndAddAnother(self):
        uuidstr = '00001111000011110000111100001111'
        id = str(uuid.UUID(uuidstr))
        reminder = WorkLogReminder(reminder_id=id, user=self.user, date=self.last_week)
        reminder.save()
        jobs = reminder.get_available_jobs()
        job = jobs[0]
        
        with self.scoped_login(username='master', password='password'):
        
            data = {'submit_and_add_another':'','hours':'4', 'text':'description', 'job':job.pk}
            response = self.client.post('/worklog/add/reminder_{0}/'.format(id), data)
            
            self.assertRedirects(response, '/worklog/add/reminder_{0}/'.format(id))
            
            items = WorkItem.objects.all()
            self.assertEquals(items.count(),1)
            
            item = items[0]
            self.assertEquals(item.date, self.last_week)
            self.assertEquals(item.hours, 4)
            self.assertEquals(item.job, job)
            
    def test_previousItemsTable(self):
        job = Job.objects.filter(name="Job_Today")[0]
        item = WorkItem(user=self.user, date=self.today, hours=3, 
                        text='My work today.', job=job)
        item.save()
        
        with self.scoped_login('master', 'password'):
            response = self.client.get('/worklog/add/')
            self.assertEquals(response.context['reminder_id'],None)
            
            self.assertEquals(len(response.context['items']),1)
            items = response.context['items']
            
            # order of columns depends on configuration, so just check that they exist
            self.assertTrue(job in items[0])        
            self.assertTrue(self.user in items[0])  
            self.assertTrue(3 in items[0])        
            
    def test_previousItemsTableReminder(self):
        """Test that previous items table works correctly with reminders."""
        # create the reminder
        uuidstr = '00001111000011110000111100001111'
        id = str(uuid.UUID(uuidstr))
        reminder = WorkLogReminder(reminder_id=id, user=self.user, date=self.last_week)
        reminder.save()
        
        # create some work log entries
        job1 = Job.objects.get(name="Job_LastWeek")
        item1= WorkItem(user=self.user, date=self.last_week, hours=3, 
                        text='Should be visible in table.', job=job1)
        job2 = Job.objects.get(name="Job_Today")
        item2 = WorkItem(user=self.user, date=self.today, hours=5, 
                        text='Should not be visible in table.', job=job2)
        item1.save()
        item2.save()
        
        with self.scoped_login(username='master', password='password'):
            response = self.client.get('/worklog/add/reminder_{0}/'.format(id))
            
            self.assertEquals(response.context['reminder_id'],id)
            
            self.assertEquals(len(response.context['items']),1)
            items = response.context['items']
            
            # order of columns depends on configuration, so just check that they exist
            self.assertTrue(job1 in items[0])        
            self.assertTrue(self.user in items[0])  
            self.assertTrue(3 in items[0])   
        
        
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


class ViewWork_TestCase(Worklog_TestCaseBase):
    def setUp(self):
        super(ViewWork_TestCase,self).setUp()
        # create some work items
        items = [
            # user, date, hours, text, job
            (self.user, self.today, 1, "item1", Job.objects.filter(name="Job_Today")[0]),
            (self.user, self.today, 2, "item2", Job.objects.filter(name="Job_OneDay")[0]),
            (self.user, self.today, 3, "item3", Job.objects.filter(name="Job_LastWeek2")[0]),
            
            (self.user, self.yesterday, 4, "item4", Job.objects.filter(name="Job_OneDay")[0]),
            (self.user, self.tomorrow, 5, "item5", Job.objects.filter(name="Job_LastWeek2")[0]),
            (self.user, self.last_week, 6, "item6", Job.objects.filter(name="Job_Today")[0]),
            
            (self.user2, self.today, 7, "item7", Job.objects.filter(name="Job_Today")[0]),
            ]
        for item in items:
            wi = WorkItem.objects.create(user=item[0], date=item[1], hours=item[2], text=item[3], job=item[4])
            wi.save()
    
    def test_basic(self):
        with self.scoped_login(username='master', password='password'):
        
            response = self.client.get('/worklog/view/')
            self.assertEquals(len(response.context['items']),7)
            self.assertEquals(response.context['menulink_base'],'')
            self.assertEquals(len(response.context['current_filters']),0)
    
    def test_badDate(self):
        with self.scoped_login(username='master', password='password'):
        
            response = self.client.get('/worklog/view/9876-22-33_/')
            self.assertEquals(len(response.context['items']),7)
            self.assertNotEquals(response.context['menulink_base'],'')
            self.assertEquals(len(response.context['current_filters']),1)
    
    def test_badUser(self):
        with self.scoped_login(username='master', password='password'):
        
            response = self.client.get('/worklog/view/?user=999')
            self.assertEquals(len(response.context['items']),0)
            self.assertEquals(response.context['menulink_base'],'')
            self.assertEquals(len(response.context['current_filters']),1)
    
    def test_badUser2(self):
        with self.scoped_login(username='master', password='password'):
        
            response = self.client.get('/worklog/view/badusername/')
            self.assertEquals(len(response.context['items']),0)
            self.assertNotEquals(response.context['menulink_base'],'')
            self.assertEquals(len(response.context['current_filters']),1)
    
    def test_badJob(self):
        with self.scoped_login(username='master', password='password'):
        
            response = self.client.get('/worklog/view/?job=999')
            self.assertEquals(len(response.context['items']),0)
            self.assertEquals(response.context['menulink_base'],'')
            self.assertEquals(len(response.context['current_filters']),1)
    
    def test_today(self):
        with self.scoped_login(username='master', password='password'):
        
            response = self.client.get('/worklog/view/today/')
            self.assertEquals(len(response.context['items']),4)
            self.assertNotEquals(response.context['menulink_base'],'')
            self.assertEquals(len(response.context['current_filters']),2) # 2, one for datemin, one for datemax
            
            i = response.context['column_names'].index('Task')  # Task corresponds to WorkItem.text
            texts = list(x[i] for x in response.context['items'])
            texts.sort()
            self.assertEqual(texts,['item1','item2','item3','item7',])
    
    def test_today2(self):
        with self.scoped_login(username='master', password='password'):
        
            response = self.client.get('/worklog/view/?datemin={0}&datemax={0}'.format(self.today))
            self.assertEquals(len(response.context['items']),4)
            self.assertEquals(response.context['menulink_base'],'')
            self.assertEquals(len(response.context['current_filters']),2) # 2, one for datemin, one for datemax
            
            i = response.context['column_names'].index('Task')  # Task corresponds to WorkItem.text
            texts = list(x[i] for x in response.context['items'])
            texts.sort()
            self.assertEqual(texts,['item1','item2','item3','item7',])
    
    def test_user(self):
        with self.scoped_login(username='master', password='password'):
        
            response = self.client.get('/worklog/view/user2/')
            self.assertEquals(len(response.context['items']),1)
            self.assertNotEquals(response.context['menulink_base'],'')
            self.assertEquals(len(response.context['current_filters']),1) 
            
            i = response.context['column_names'].index('Task')  # Task corresponds to WorkItem.text
            texts = list(x[i] for x in response.context['items'])
            texts.sort()
            self.assertEqual(texts,['item7',])
    
    def test_userToday(self):
        with self.scoped_login(username='master', password='password'):
        
            response = self.client.get('/worklog/view/master/today/')
            self.assertEquals(len(response.context['items']),3)
            self.assertNotEquals(response.context['menulink_base'],'')
            self.assertEquals(len(response.context['current_filters']),3)
            
            i = response.context['column_names'].index('Task')  # Task corresponds to WorkItem.text
            texts = list(x[i] for x in response.context['items'])
            texts.sort()
            self.assertEqual(texts,['item1','item2','item3',])
    
    def test_dateRange(self):
        with self.scoped_login(username='master', password='password'):
        
            response = self.client.get('/worklog/view/?datemin={0}&datemax={1}'.format(self.last_week,self.yesterday))
            self.assertEquals(len(response.context['items']),2)
            self.assertEquals(response.context['menulink_base'],'')
            self.assertEquals(len(response.context['current_filters']),2) # 2, one for datemin, one for datemax
            
            i = response.context['column_names'].index('Task')  # Task corresponds to WorkItem.text
            texts = list(x[i] for x in response.context['items'])
            texts.sort()
            self.assertEqual(texts,['item4','item6',])


class SendReminderEmails_TestCase(Worklog_TestCaseBase):
    def setUp(self):
        super(SendReminderEmails_TestCase,self).setUp()
        self.user3 = User.objects.create_user(username="user3", email="user3@example.com", password="password")
        self.user4 = User.objects.create_user(username="user4", email="user4@example.com", password="password")
        self.user5 = User.objects.create_user(username="user5", email="user5@example.com", password="password")
        
    def tearDown(self):
        # Delete all test users.
        self.user3.delete()
        self.user4.delete()
        self.user5.delete()
        super(SendReminderEmails_TestCase,self).tearDown()
        
    def test_basic(self):
        # create some work items
        items = [
            # user, date, hours, text, job
            (self.user, self.today, 1, "item1", Job.objects.filter(name="Job_Today")[0]),
            (self.user2, self.today, 2, "item2", Job.objects.filter(name="Job_Today")[0]),
            (self.user2, self.yesterday, 3, "item3", Job.objects.filter(name="Job_Today")[0]),
            (self.user3, self.yesterday, 4, "item4", Job.objects.filter(name="Job_Today")[0]),
            (self.user4, self.last_week, 5, "item5", Job.objects.filter(name="Job_Today")[0]),
            (self.user5, self.tomorrow, 6, "item6", Job.objects.filter(name="Job_Today")[0]),
            ]
        for item in items:
            wi = WorkItem.objects.create(user=item[0], date=item[1], hours=item[2], text=item[3], job=item[4])
            wi.save()
        
        # try to send emails
        tasks.send_reminder_emails()
        
        self.assertEquals(len(mail.outbox), 3) # user3, user4, user5
        all_recipients = list(m.to[0] for m in mail.outbox)
        self.assertEquals(len(all_recipients), 3)
        self.assertTrue("user3@example.com" in all_recipients)
        self.assertTrue("user4@example.com" in all_recipients)
        self.assertTrue("user5@example.com" in all_recipients)
        
        qs = WorkLogReminder.objects.all()
        self.assertEquals(qs.count(), 3)
        
    def test_empty(self):
        # create some work items
        items = [
            # user, date, hours, text, job
            (self.user, self.today, 1, "item1", Job.objects.filter(name="Job_Today")[0]),
            (self.user2, self.today, 2, "item2", Job.objects.filter(name="Job_Today")[0]),
            (self.user3, self.today, 3, "item3", Job.objects.filter(name="Job_Today")[0]),
            (self.user4, self.today, 4, "item4", Job.objects.filter(name="Job_Today")[0]),
            (self.user5, self.today, 5, "item5", Job.objects.filter(name="Job_Today")[0]),
            ]
        for item in items:
            wi = WorkItem.objects.create(user=item[0], date=item[1], hours=item[2], text=item[3], job=item[4])
            wi.save()
        
        # try to send emails
        tasks.send_reminder_emails()
        
        self.assertEquals(len(mail.outbox), 0)
        all_recipients = list(m.to[0] for m in mail.outbox)
        self.assertEquals(len(all_recipients), 0)
        
        qs = WorkLogReminder.objects.all()
        self.assertEquals(qs.count(), 0)

def suite():
    test_suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    test_suite.addTest(loader.loadTestsFromTestCase(CreateWorkItem_TestCase))
    test_suite.addTest(loader.loadTestsFromTestCase(ClearExpiredReminders_TestCase))
    test_suite.addTest(loader.loadTestsFromTestCase(ViewWork_TestCase))
    test_suite.addTest(loader.loadTestsFromTestCase(SendReminderEmails_TestCase))
    return test_suite



