"""
dependencies.py

Dependency functions for FastAPI project:
- get_current_user: Retrieves and validates the current user from the request.
- get_db_session: Provides a database session per request.
- pagination_params: Parses pagination parameters from query.
- require_admin: Ensures user has admin privileges.
"""

from typing import Any, Generator, Optional
from contextlib import contextmanager
import os
import sys
import re

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from models import User
from database import SessionLocal
from core import auth


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@contextmanager
def db_session_context() -> Generator[Session, None, None]:
    """
    Context manager for SQLAlchemy session.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session for each request.

    Yields:
        Session: SQLAlchemy session.
    """
    with db_session_context() as session:
        yield session


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db_session)
) -> User:
    """
    Dependency that retrieves the current user using the provided token.

    Args:
        token (str): JWT token from request.
        db (Session): Database session.

    Returns:
        User: Authenticated user object.

    Raises:
        HTTPException: If authentication fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = auth.decode_access_token(token)
    if not payload or "sub" not in payload:
        raise credentials_exception
    user_id: int = payload["sub"]
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception
    return user


def pagination_params(
    request: Request
) -> dict[str, Any]:
    """
    Dependency that parses pagination parameters from query.

    Args:
        request (Request): FastAPI request object.

    Returns:
        dict[str, Any]: Pagination parameters: limit, offset.
    """
    try:
        limit = int(request.query_params.get("limit", 20))
        offset = int(request.query_params.get("offset", 0))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination parameters"
        )
    if limit < 1 or offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pagination parameters out of range"
        )
    return {"limit": limit, "offset": offset}


def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency that ensures the user has admin privileges.

    Args:
        current_user (User): Authenticated user object.

    Returns:
        User: Admin user object.

    Raises:
        HTTPException: If user is not admin.
    """
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user