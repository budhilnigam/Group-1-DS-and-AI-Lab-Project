"""Configuration classes for Flask application.

This module contains configuration settings for different environments:
Development, Production, and Testing. Each class defines the necessary
settings such as SECRET_KEY and DATABASE_URI.
"""

import os
import sys
import re

import os
from typing import Any


class Config:
    """Base configuration class with common settings."""

    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'default_secret_key')
    DATABASE_URI: str = os.environ.get('DATABASE_URI', 'sqlite:///:memory:')
    DEBUG: bool = False
    TESTING: bool = False

    @staticmethod
    def init_app(app: Any) -> None:
        """Initialize the application with the given configuration."""
        pass


class DevelopmentConfig(Config):
    """Configuration settings for development environment."""

    DEBUG: bool = True
    DATABASE_URI: str = os.environ.get('DEV_DATABASE_URI', 'sqlite:///dev.db')


class ProductionConfig(Config):
    """Configuration settings for production environment."""

    DATABASE_URI: str = os.environ.get('PROD_DATABASE_URI', 'mysql://user:password@localhost/prod')


class TestingConfig(Config):
    """Configuration settings for testing environment."""

    TESTING: bool = True
    DATABASE_URI: str = os.environ.get('TEST_DATABASE_URI', 'sqlite:///:memory:')
    SECRET_KEY: str = os.environ.get('TEST_SECRET_KEY', 'test_secret_key')


configurations = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}