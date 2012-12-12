# Worklog - Time Management for the Rest of Us #

## Overview ##

Worklog is a Django-based, hourly work logging web application that supports work item entry, job costing, job funding, burn-down charting, work item filtering, CSV report generation, and an e-mail reminder system.

## Project Configuration ##

### Required settings.py Parameters ###

#### Site URL ####

Add new entry for the site url in the admin/sites. This must be fully qualified and it must not include a closing slash. Update corresponding SITE_ID in settings.py. We can use 'http://127.0.0.1:8000' for local dev environment.

#### Site Admins ####

You should have at least one admin user set up in your settings.py file because that is where Worklog will send all invoice and timesheet reports to.

### Default Behavior ###

Email reminder records are cleared from the database after 14 days.
Reminder emails are sent every weekday at 6pm.
Reminder records are cleared from the database every weekday at 7pm.

## Functionality ##

### Charting ###

Burn down charts are provided to view funding vs. hourly consumption for individual jobs. The charting interface can be accessed at: '/worklog/chart/'

#### Parameters ####

In order to view burn down charts related to a job, you may use the provided web interface or provide the values using the following GET parameters:

	* job_id - The ID of the job that you wish to view the data for.
	* start_date (optional) - The date to use for the start of the data reported. The format is mm/dd/yyyy.
	* end_date (optional) - The date to use for the end of the data reported. The format is mm/dd/yyyy.

If you do not provide the start and end date, the data will start at the first available date of funding and end at the date of the last submitted work item.

### Job Creation with Time Allocation ###

Create new jobs for employees to log hours into. Each job can be allocated a certain number of hours which will produce very nice burn rate charts (see above.). Each job can be associated with one or more users. By default a job is associated with all users. This can be disabled by deselecting the "Available all users" check box and select only some users. A user can create work items only for the jobs that he/she is part of.

### Holidays ###

Add certain dates as holidays.  Work items can still be entered on holidays, but bi-weekly timesheets will not include those work items.  For bi-weekly employees, a note is shown on the work item entry form indicating that day is a holiday.

### From Email address ###
All emails are sent from the email address configured in settings.py through DEFAULT_FROM_EMAIL

```DEFAULT_FROM_EMAIL = '"Friday Institute Worklog" <fi-worklog@ncsu.edu>'```

### Reminder Emails ###

Automatically send all active users a reminder to log their hours if they haven't done so already that particular day. These emails are sent daily but can be customized.   

__NOTE: A user must be 'active' to recieve reminder emails.__

#### Remind Email Options ####

	# These settings aren't required, but defined for convenience
    everyday = [0,1,2,3,4,5,6]
    weekdays = [1,2,3,4,5]

Email reminder records are cleared from the database after this many days. E.g. after 2 weeks
WORKLOG_EMAIL_REMINDERS_EXPIRE_AFTER = 14

The time and days to send reminder emails. E.g. 6pm during each workday
WORKLOG_SEND_REMINDERS_HOUR = 18
WORKLOG_SEND_REMINDERS_DAYSOFWEEK = weekdays

The time and days to clear reminder records from the database. E.g. 7pm during each workday
WORKLOG_CLEAR_REMINDERS_HOUR = 19
WORKLOG_CLEAR_REMINDERS_DAYSOFWEEK = weekdays

__NOTE: For more information about formatting and periodic tasks, visit http://packages.python.org/celery/userguide/periodic-tasks.html__

### Invoicing ###

Invoices can be generated for certain jobs using the amount of logged hours from all employees. Invoices are emailed to the admins nightly at 2am (which can be customized, as well). Every job has an option of 'Do Not Invoice' which will omit it from the report. Individual work items can be marked as 'Do Not Invoice' or as 'Already Invoiced'. Once an invoice is sent to the admin's email, it will contain a link. This link will lead you to page where you can actually generate an invoice report (which will then be sent to your email), or invoice all items, which will override your current preferences for all jobs.

### Generating Time Sheets (NCSU Specific) ###

Time sheets are generated for bi-weekly employees only. On the night that a time sheet is due, an email will be sent to the site administrators informing them that this is the case. The email will contain a URL which will allow admins to send time sheets to specific employees or to all employees at once.   

__NOTE: Bi-weekly employees must be configured for this to work.__  
__NOTE: This only works once Work Periods have been added to the admin interface.__

## To Log Hours ##

Once a user is logged in, they must go to the following URL: 'worklog/add/'
There, a user will enter the amount of hours worked, select a 'job' from the dropdown and explain in a few words what was worked on specifically. From there you can either exit the form or add another job for the day. Note that this form **only** logs hours for the current day's date.

## Time Zone Settings ##

All times will be in UTC unless the following is placed in your settings.py file:
CELERY_ENABLE_UTC = True

It is also recommended to include the following in the settings.py file:
CELERY_TIMEZONE = 'America/New_York'

Read more: http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html#timezones
