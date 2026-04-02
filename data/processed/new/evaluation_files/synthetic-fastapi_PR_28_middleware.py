"""
middleware.py

Custom FastAPI middleware for request timing and structured logging.

This module provides RequestTimingMiddleware and LoggingMiddleware
to monitor request durations and log request/response information
in a structured manner.
"""

import time
import logging
import uuid
import os
import sys
import re
from typing import Callable, Awaitable
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to measure and record request processing time.
    Adds 'X-Process-Time' header to each response.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.6f}"
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured logging of requests and responses.
    Logs method, path, status code, process time, and unique request ID.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.logger = logging.getLogger("fastapi.middleware")
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt=(
                '{"time":"%(asctime)s","level":"%(levelname)s",'
                '"message":"%(message)s","request_id":"%(request_id)s"}'
            ),
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        method = request.method
        path = request.url.path

        self.logger.info(
            f"Request started: {method} {path}",
            extra={"request_id": request_id},
        )

        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        log_data = {
            "method": method,
            "path": path,
            "status_code": response.status_code,
            "process_time": round(process_time, 6),
        }

        self.logger.info(
            f"Request completed: {log_data}",
            extra={"request_id": request_id},
        )

        response.headers["X-Request-ID"] = request_id
        return response