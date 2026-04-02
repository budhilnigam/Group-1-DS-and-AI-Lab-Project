"""
Utility functions for common tasks in the Django project.

This module includes helper functions for:
- Generating unique slugs for models
- Retrieving the client's IP address from a request
- Sending notification emails
"""

import random
import string
from typing import Optional
from django.db.models import Model
from django.http import HttpRequest
from django.core.mail import send_mail
from django.utils.text import slugify


def generate_unique_slug(instance: Model, field_value: str, slug_field_name: str = "slug") -> str:
    """
    Generate a unique slug for a given model instance.
    """
    base_slug = slugify(field_value)
    unique_slug = base_slug
    model_class = instance.__class__
    counter = 1

    # Ensure the slug is unique by appending a counter if necessary
    while model_class.objects.filter(**{slug_field_name: unique_slug}).exclude(id=instance.id).exists():
        unique_slug = f"{base_slug}-{counter}"
        counter += 1

    return unique_slug


def get_client_ip(request: HttpRequest) -> Optional[str]:
    """
    Retrieve the client's IP address from a Django request object.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def send_notification_email(subject: str, message: str, recipient_list: list[str] = [], from_email: Optional[str] = None) -> bool:
    """
    Send a notification email to a list of recipients.
    """
    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        return True
    except Exception as e:
        # Log the exception in real-world scenarios
        print(f"Error sending email: {e}")
        return False