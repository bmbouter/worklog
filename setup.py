import os
from setuptools import setup

def read(fname):
  return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name = "Worklog",
          version = "0.8",
          author = "Brian Bouterse",
          author_email = "bmbouter@gmail.com",
          description = ("A Django based, hourly work logging app which supports job coding, view filtering, csv report generation and an e-mail reminder system"),
          keywords = "Work logging, Report, Email reminder",
	  url = "https://www.fi.ncsu.edu/",
          packages=['worklog'],
	  #README.md need to be renamed as README
	  long_description=read('README'),
          classifiers=[ "Development Status :: 4 - Beta","Topic :: Utilities","License :: OSI Approved :: BSD License", 
          ],
          install_requires=[
                            "django==1.4.1",
                            "celery==3.0.9",
                            "django-celery==3.0.9",
                            "xhtml2pdf",
                            "pisa",
                            "south",
                            "gunicorn",
                            "pytz",
                            "flake8",
                           ],
)
