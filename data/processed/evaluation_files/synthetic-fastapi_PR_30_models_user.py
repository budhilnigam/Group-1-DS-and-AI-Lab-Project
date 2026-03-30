"""
User model definition for FastAPI project.

Defines the SQLAlchemy User model with id, username, email, hashed_password,
is_active, and created_at columns, including constraints and utility methods.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    """
    SQLAlchemy User model.

    Attributes:
        id (int): Primary key.
        username (str): Unique username.
        email (str): Unique email address.
        hashed_password (str): Hashed password.
        is_active (bool): User activation status.
        created_at (datetime): Creation timestamp.
    """
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, index=True)
    username: str = Column(String(64), unique=True, nullable=False, index=True)
    email: str = Column(String(128), unique=True, nullable=False, index=True)
    hashed_password: str = Column(String(256), nullable=False)
    is_active: bool = Column(Boolean, default=True, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        """
        Return a string representation of the User instance.

        Returns:
            str: String representation.
        """
        return (
            f"<User(id={self.id}, username='{self.username}', "
            f"email='{self.email}', is_active={self.is_active}, "
            f"created_at='{self.created_at}')>"
        )

    def activate(self) -> None:
        """
        Activate the user account.
        """
        self.is_active = True

    def deactivate(self) -> None:
        """
        Deactivate the user account.
        """
        self.is_active = False

    def set_password(self, hashed_password: str) -> None:
        """
        Set the user's hashed password.

        Args:
            hashed_password (str): The hashed password.
        """
        self.hashed_password = hashed_password

    def checkUsername(self, username: str) -> bool:
        """
        Check if the provided username matches this user's username.

        Args:
            username (str): Username to check.

        Returns:
            bool: True if matches, False otherwise.
        """
        return self.username == username

    def checkEmail(self, email: str) -> bool:
        """
        Check if the provided email matches this user's email.

        Args:
            email (str): Email to check.

        Returns:
            bool: True if matches, False otherwise.
        """
        return self.email == email