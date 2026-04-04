"""
Custom middleware module for a Django project.

This module includes two middleware classes:
1. TimingMiddleware: Measures the time taken to process each request.
2. RequestLoggingMiddleware: Logs details of incoming requests.

Both middleware classes implement the `__init__` and `__call__` methods
to integrate with Django's middleware processing.
"""

import time
import logging
from typing import Callable
from django.http import HttpRequest, HttpResponse
import os
import sys
import re

logger = logging.getLogger(__name__)

class TimingMiddleware:
    """
    Middleware to measure the time taken to process each request.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start_time = time.time()
        response = self.get_response(request)
        end_time = time.time()
        duration = end_time - start_time

        logger.info(
            "Request to %s took %.2f seconds",
            request.path,
            duration
        )
        response["X-Process-Time"] = f"{duration:.2f}s"
        return response


class RequestLoggingMiddleware:
    """
    Middleware to log details of incoming requests.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        logger.info(
            "Incoming request: method=%s, path=%s, remote_addr=%s, user_agent=%s",
            request.method,
            request.path,
            self._get_client_ip(request),
            request.META.get("HTTP_USER_AGENT", "unknown")
        )
        return self.get_response(request)

    def _get_client_ip(self, request: HttpRequest) -> str:
        """
        Extracts the client's IP address from the request.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")