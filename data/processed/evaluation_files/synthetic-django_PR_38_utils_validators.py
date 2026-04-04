"""
Custom validation utilities for Django models and forms.

This module contains custom validators to be used across the Django project.
The functions include validation for image file size, slug format, and profanity filtering.
"""

import re
import os
import sys
from typing import Any, List

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_image_size(image: Any, max_size_mb: int = 5) -> None:
    """
    Validates that the uploaded image does not exceed the specified size.

    Args:
        image (Any): The image file to validate.
        max_size_mb (int): The maximum allowed size in megabytes. Defaults to 5MB.

    Raises:
        ValidationError: If the image size exceeds the maximum allowed limit.
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    if image.size > max_size_bytes:
        raise ValidationError(
            _('Image size should not exceed %(max_size_mb)dMB.'),
            params={'max_size_mb': max_size_mb},
        )


def validate_slug_format(slug: str, allowed_chars: List[str] = []) -> None:
    """
    Validates that a string is a properly formatted slug.

    Args:
        slug (str): The string to validate.
        allowed_chars (List[str]): Additional allowed characters for the slug. Defaults to empty list.

    Raises:
        ValidationError: If the string is not a valid slug.
    """
    slug_regex = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
    if not re.match(slug_regex, slug):
        raise ValidationError(
            _('Enter a valid slug consisting of lowercase letters, numbers, and hyphens.'),
            code='invalid_slug',
        )


def validate_no_profanity(value: str, profane_words: set = {'badword1', 'badword2', 'badword3'}) -> None:
    """
    Validates that a string does not contain any profane words.

    Args:
        value (str): The string to validate.
        profane_words (set): A set of profane words to check against. Defaults to predefined set.

    Raises:
        ValidationError: If the string contains any profanity.
    """
    words = value.lower().split()
    for word in words:
        if word in profane_words:
            raise ValidationError(
                _('The text contains inappropriate language: "%(word)s".'),
                params={'word': word},
                code='profanity_detected',
            )