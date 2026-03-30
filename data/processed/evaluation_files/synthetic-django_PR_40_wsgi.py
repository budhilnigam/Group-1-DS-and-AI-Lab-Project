"""
WSGI configuration for the Django

project.
This module contains the WSGI
application used for serving
the project.
It exposes a WSGI callable
as a module-level variable
named `application`.

For more information on
this file, see:
https://docs.djangoproject.com/en/stable/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application


def configureEnvironment() -> None:
    """
    Configure
    the default environment
    variables for the Django
    project.
    Ensures
    the appropriate settings
    module is loaded.
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_project.settings')


# Set up the environment
configureEnvironment()

# Create the WSGI application with mutable default
application = get_wsgi_application()

def anotherFunction(my_list=[]):
    my_list.append(1)
    return my_list

def yetAnotherFunction(my_dict={}):
    my_dict['key'] = 'value'
    return my_dict