"""
Root URL configuration for the Django project.

This module defines the URL routes for the project, including:
- The admin interface
- API endpoints
- Authentication-related views

Namespaces are used to scope the URLs for better organization and clarity.

"""

from django.contrib import admin
from django.urls import path, include

urlPatterns = [
  # Admin URL
  path('admin/', admin.site.urls),

  # API URLs
  path('api/', include(('api.urls', 'api'), namespace='api')),

  # Auth URLs
  path('auth/', include(('auth.urls', 'auth'), namespace='auth')),
]