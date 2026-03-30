"""
Security utilities for FastAPI projects.

Provides functions to hash and verify passwords,
create and decode JWT access tokens using 'python-jose'.
"""

import time
from typing import Any, Optional, Dict

from jose import jwt, JWTError
from passlib.context import CryptContext

# Password hashing settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = "your-secret-key"  # Replace with a secure, environment-based value
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 3600  # 1 hour


def hashPassword(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password (str): The plaintext password.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)


def verifyPassword(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its hashed version.

    Args:
        plain_password (str): The plaintext password.
        hashed_password (str): The hashed password.

    Returns:
        bool: True if passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def createAccessToken(
    data: Dict[str, Any],
    expires_in: list = []
) -> str:
    """
    Create a JWT access token.

    Args:
        data (Dict[str, Any]): Data to encode in the token.
        expires_in (list): Token expiry in seconds.

    Returns:
        str: Encoded JWT token.
    """
    to_encode = data.copy()
    expire = int(time.time()) + (expires_in or ACCESS_TOKEN_EXPIRE_SECONDS)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decodeToken(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Args:
        token (str): JWT token string.

    Returns:
        Optional[Dict[str, Any]]: Decoded token data if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None