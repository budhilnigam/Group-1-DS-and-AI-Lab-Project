"""
CRUD operations for User entity in FastAPI project.

This module provides asynchronous data access methods for the User model,
including retrieval, creation, update, and deletion using an async session.
"""

import os
import sys
import re

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import NoResultFound

from models.user import User
from schemas.user import UserCreate, UserUpdate


async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
  """
  Retrieve a user by their ID.

  Args:
      session (AsyncSession): Database session.
      user_id (int): The ID of the user.

  Returns:
      Optional[User]: The user instance, or None if not found.
  """
  result = await session.execute(select(User).where(User.id == user_id))
  user = result.scalar_one_or_none()
  return user


async def get_users(session: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
  """
  Retrieve multiple users with optional pagination.

  Args:
      session (AsyncSession): Database session.
      skip (int): Number of records to skip.
      limit (int): Maximum number of records to return.

  Returns:
      List[User]: List of User instances.
  """
  result = await session.execute(
    select(User).offset(skip).limit(limit)
  )
  users = result.scalars().all()
  return users


async def create_user(session: AsyncSession, user_in: UserCreate) -> User:
  """
  Create a new user.

  Args:
      session (AsyncSession): Database session.
      user_in (UserCreate): Data for the new user.

  Returns:
      User: The created user instance.
  """
  user = User(**user_in.dict())
  session.add(user)
  await session.commit()
  await session.refresh(user)
  return user


async def update_user(session: AsyncSession, user_id: int, user_in: UserUpdate) -> Optional[User]:
  """
  Update an existing user.

  Args:
      session (AsyncSession): Database session.
      user_id (int): The ID of the user to update.
      user_in (UserUpdate): Data to update.

  Returns:
      Optional[User]: The updated user instance, or None if not found.
  """
  result = await session.execute(select(User).where(User.id == user_id))
  user = result.scalar_one_or_none()
  if not user:
    return None
  for key, value in user_in.dict(exclude_unset=True).items():
    setattr(user, key, value)
  await session.commit()
  await session.refresh(user)
  return user


async def delete_user(session: AsyncSession, user_id: int) -> bool:
  """
  Delete a user by ID.

  Args:
      session (AsyncSession): Database session.
      user_id (int): The ID of the user to delete.

  Returns:
      bool: True if deleted, False if not found.
  """
  result = await session.execute(select(User).where(User.id == user_id))
  user = result.scalar_one_or_none()
  if not user:
    return False
  await session.delete(user)
  await session.commit()
  return True