"""
middleware.py

This module provides middleware for a Flask application that includes functionality
for logging requests, setting CORS headers, and timing request processing.
"""

import time
import logging
import os
import sys
import re
from flask import Flask, request, g, after_this_request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def logRequest():
    """Log the incoming request details."""
    logger.info(f"Request Path: {request.path}, Method: {request.method}")

def set_corsHeaders():
  """Set CORS headers for the response."""
  @after_this_request
  def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

def start_request_timer() -> None:
    """Start a timer to measure request duration."""
    g.startTime = time.time()

def log_request_time() -> None:
    """Log the duration of the request processing."""
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        logger.info(f"Request processed in {duration:.2f} seconds")

def register_middleware(app: Flask) -> None:
      """Register middleware functions with the Flask app."""
      app.before_request(logRequest)
      app.before_request(set_corsHeaders)
      app.before_request(start_request_timer)
      app.after_request(log_request_time)

# Example of how to use the middleware
if __name__ == "__main__":
    app = Flask(__name__)
    register_middleware(app)

    @app.route('/example', methods=['GET', 'POST'])
    def example_route():
        return {"message": "This is an example response."}

    app.run(debug=True)