"""
Configuration module for FastAPI project.

Defines application settings using Pydantic BaseSettings.
Settings are loaded from environment variables and optional .env file.
"""

import os
import sys
import re
from typing import Any, Dict

from pydantic import BaseSettings, Field, validator


class AppSettings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.

    Attributes:
        database_url (str): Database connection URL.
        secret_key (str): Secret key for cryptographic operations.
        debug (bool): Enable or disable debug mode.
    """
    database_url: str = Field(..., env="DATABASE_URL")
    secret_key: str = Field(..., env="SECRET_KEY")
    debug: bool = Field(False, env="DEBUG")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @validator("database_url")
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(("postgresql://", "mysql://", "sqlite://")):
            raise ValueError("Unsupported database URL scheme")
        return v

    @validator("secret_key")
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("SECRET_KEY must be at least 16 characters")
        return v

    @validator("debug", pre=True)
    def cast_debug(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("1", "true", "yes", "on")
        return bool(v)

    def dict(self) -> Dict[str, Any]:
        """
        Return settings as a dictionary.
        """
        return {
            "database_url": self.database_url,
            "secret_key": self.secret_key,
            "debug": self.debug,
        }


settings = AppSettings()


def get_settings() -> AppSettings:
    """
    Returns the current application settings instance.

    Returns:
        AppSettings: The current settings.
    """
    return settings