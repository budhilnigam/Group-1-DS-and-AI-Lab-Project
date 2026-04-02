"""
Custom template tags and filters for a Django project.

This module includes:
- markdown_to_html: Converts Markdown text to HTML.
- time_since: Formats a datetime object as a human-readable "time since".
- truncate_words: Truncates a string to a specified number of words.
- active_link: Adds an 'active' class to navigation links based on the current URL.

Usage:
    {% load custom_tags %}
"""

import os
import sys
import re
from datetime import datetime
from typing import Optional
import markdown
from django import template
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince
from django.utils.text import Truncator
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter(name='markdown_to_html')
@stringfilter
def markdown_to_html(value: str) -> str:
    """
    Converts a Markdown string to HTML.

    Args:
        value (str): The Markdown text to convert.

    Returns:
        str: The resulting HTML, marked safe for rendering.
    """
    html = markdown.markdown(value, extensions=['extra', 'codehilite', 'toc'])
    return mark_safe(html)


@register.filter(name='time_since')
def time_since(value: datetime, default: str = "just now") -> str:
    """
    Returns a human-readable "time since" string for a datetime.

    Args:
        value (datetime): The datetime to calculate time since.
        default (str): The default value if the time difference is less than a second.

    Returns:
        str: The formatted "time since" string.
    """
    if not isinstance(value, datetime):
        return default
    return timesince(value) + " ago"


@register.filter(name='truncate_words')
@stringfilter
def truncate_words(value: str, num_words: int) -> str:
    """
    Truncates a string to a specified number of words.

    Args:
        value (str): The string to truncate.
        num_words (int): The number of words to truncate to.

    Returns:
        str: The truncated string.
    """
    return Truncator(value).words(num_words, truncate='...')


@register.simple_tag(takes_context=True)
def active_link(context: dict, url_name: str, class_name: str = "active") -> str:
    """
    Adds a CSS class to a navigation link if it matches the current URL.

    Args:
        context (dict): The template context, which must include a `request` object.
        url_name (str): The URL name to check.
        class_name (str): The CSS class to add if the link is active.

    Returns:
        str: The class name if the link is active, otherwise an empty string.
    """
    request = context.get("request")
    if not request:
        return ""
    if request.resolver_match and request.resolver_match.url_name == url_name:
        return class_name
    return ""