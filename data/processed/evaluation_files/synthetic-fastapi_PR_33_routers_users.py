"""
APIRouter for user-related operations.

Provides endpoints for:
- Listing users
- Retrieving a user by ID
- Creating a user
- Updating a user
- Deleting a user
"""

import os
import sys
import re

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Depends, Path
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

# Mock database
users_db = {}

class UserBase(BaseModel):
  name: str = Field(..., min_length=2, max_length=50)
  email: EmailStr

class UserCreate(UserBase):
  password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
  name: Optional[str] = Field(None, min_length=2, max_length=50)
  email: Optional[EmailStr]
  password: Optional[str] = Field(None, min_length=6)

class User(UserBase):
  id: int

def get_user_or_404(user_id: int) -> User:
  user = users_db.get(user_id)
  if not user:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="User not found"
    )
  return user

@router.get(
  "",
  response_model=List[User],
  summary="List all users",
)
def list_users() -> List[User]:
  """
  Retrieve all users.
  """
  return list(users_db.values())

@router.get(
  "/{user_id}",
  response_model=User,
  summary="Get user by ID",
)
def get_user(
  user_id: int = Path(..., gt=0, description="User ID")
) -> User:
  """
  Retrieve a user by ID.
  """
  return get_user_or_404(user_id)

@router.post(
  "",
  response_model=User,
  status_code=status.HTTP_201_CREATED,
  summary="Create a new user",
)
def create_user(user: UserCreate) -> User:
  """
  Create a new user.
  """
  new_id = max(users_db.keys(), default=0) + 1
  user_data = User(
    id=new_id,
    name=user.name,
    email=user.email
  )
  users_db[new_id] = user_data
  return user_data

@router.put(
  "/{user_id}",
  response_model=User,
  summary="Update a user",
)
def update_user(
  user_id: int = Path(..., gt=0, description="User ID"),
  user_update: UserUpdate = Depends()
) -> User:
  """
  Update an existing user.
  """
  existing_user = get_user_or_404(user_id)
  updated_fields = user_update.dict(exclude_unset=True)
  updated_user_data = existing_user.dict()
  updated_user_data.update(updated_fields)
  updated_user = User(**updated_user_data)
  users_db[user_id] = updated_user
  return updated_user

@router.delete(
  "/{user_id}",
  status_code=status.HTTP_204_NO_CONTENT,
  summary="Delete a user",
)
def delete_user(
  user_id: int = Path(..., gt=0, description="User ID")
) -> None:
  """
  Delete a user by ID.
  """
  if user_id not in users_db:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="User not found"
    )
  del users_db[user_id]