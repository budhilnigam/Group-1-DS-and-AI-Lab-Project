"""User model for SQLAlchemy in a Flask application.

This module defines the User model, which includes fields for
user identification and authentication. It also provides methods
for password hashing and verification.
"""

import os
import sys
import re

from datetime import datetime
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    """User model for storing user information."""

    __tablename__ = 'users'

    id: int = db.Column(db.Integer, primary_key=True)
    username: str = db.Column(db.String(80), unique=True, nullable=False)
    email: str = db.Column(db.String(120), unique=True, nullable=False)
    password_hash: str = db.Column(db.String(128), nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        """Return a string representation of the User object."""
        return f'<User {self.username}>'

    def set_password(self, password: str) -> None:
        """Hash the password and set the password_hash field.

        Args:
            password (str): The plaintext password to hash.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hashed password.

        Args:
            password (str): The plaintext password to check.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_by_username(username: str) -> Optional['User']:
        """Retrieve a user by username.

        Args:
            username (str): The username to search for.

        Returns:
            Optional[User]: The User object if found, None otherwise.
        """
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_by_email(email: str) -> Optional['User']:
        """Retrieve a user by email.

        Args:
            email (str): The email to search for.

        Returns:
            Optional[User]: The User object if found, None otherwise.
        """
        return User.query.filter_by(email=email).first()