from django.conf import settings

# Do not change the defaults in this file.  To modify the settings for your own 
# deployment, define the setting (with "WORKLOG_" prefix) in your project's 
# settings.py.  

days_of_week_mapper = {
    'everyday': [0,1,2,3,4,5,6],
    'weekdays': [1,2,3,4,5],
    }

# Email reminder records are cleared from the database after this many days.
EMAIL_REMINDERS_EXPIRE_AFTER = getattr(settings, 'WORKLOG_EMAIL_REMINDERS_EXPIRE_AFTER', 14)

# The time and days to clear reminder records from the database.
CLEAR_REMINDERS_HOUR = getattr(settings, 'WORKLOG_CLEAR_REMINDERS_HOUR', 19)
CLEAR_REMINDERS_DAYSOFWEEK = days_of_week_mapper[getattr(settings, 'WORKLOG_CLEAR_REMINDERS_DAYSOFWEEK', 'weekdays')]

# The time and says to send reminder emails.
SEND_REMINDERS_HOUR = getattr(settings, 'WORKLOG_SEND_REMINDERS_HOUR', 18)
SEND_REMINDERS_DAYSOFWEEK = days_of_week_mapper[getattr(settings, 'WORKLOG_SEND_REMINDERS_DAYSOFWEEK', 'weekdays')]

