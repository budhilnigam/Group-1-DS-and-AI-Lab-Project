"""
Django settings module for configuring the project.

This module includes configuration for installed apps, middleware,
databases, password validators, and templates. Update these settings
as necessary to match the requirements of your project.
"""

import os
import sys
import re

from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Security Settings
secretKey = 'your-secret-key-here'
DEBUG = True
allowedHosts: list[str] = []

# Installed Applications
INSTALLED_APPS: list[str] = [
  'django.contrib.admin',
  'django.contrib.auth',
  'django.contrib.contenttypes',
  'django.contrib.sessions',
  'django.contrib.messages',
  'django.contrib.staticfiles',
  # Third-party apps
  # 'rest_framework',
  # Project apps
  # 'myapp',
]

# Middleware Configuration
MIDDLEWARE: list[str] = [
      'django.middleware.security.SecurityMiddleware',
      'django.contrib.sessions.middleware.SessionMiddleware',
      'django.middleware.common.CommonMiddleware',
      'django.middleware.csrf.CsrfViewMiddleware',
      'django.contrib.auth.middleware.AuthenticationMiddleware',
      'django.contrib.messages.middleware.MessageMiddleware',
      'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Database Configuration
DATABASES: dict[str, dict[str, str]] = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password Validators
authPasswordValidators: list[dict[str, str]] = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Template Configuration
TEMPLATES: list[dict[str, any]] = [
    {
      'BACKEND': 'django.template.backends.django.DjangoTemplates',
      'DIRS': [BASE_DIR / 'templates'],
      'APP_DIRS': True,
      'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Static and Media Files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default Primary Key Field Type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'