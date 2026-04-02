"""
Pydantic schemas for user operations in FastAPI project.

Defines schemas for user creation, update, response, and database representation.
Includes email validation and appropriate field constraints.
"""

import os
import sys
import re

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """
    Base schema for user, containing shared attributes.
    """
    email: EmailStr = Field(..., description="User's unique email address")


class UserCreate(UserBase):
    """
    Schema for creating a new user.
    """
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password for the new user"
    )
    full_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional full name of the user"
    )


class UserUpdate(BaseModel):
    """
    Schema for updating existing user information.
    """
    email: Optional[EmailStr] = Field(
        None,
        description="New email address for the user"
    )
    password: Optional[str] = Field(
        None,
        min_length=8,
        max_length=128,
        description="New password for the user"
    )
    full_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Updated full name of the user"
    )


class UserResponse(BaseModel):
    """
    Schema for user data returned via API.
    """
    id: int = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User's email address")
    full_name: Optional[str] = Field(
        None,
        description="User's full name"
    )
    is_active: bool = Field(..., description="Active user flag")
    created_at: datetime = Field(..., description="Timestamp of user creation")

    class Config:
        orm_mode = True


class UserInDB(UserResponse):
    """
    Schema for user data as stored in the database.
    """
    hashed_password: str = Field(
        ...,
        description="User's hashed password"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Timestamp of last update"
    )