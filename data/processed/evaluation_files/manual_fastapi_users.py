"""
FastAPI router for managing user accounts.

Provides CRUD endpoints for user resources including
registration, profile retrieval, and account updates.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, EmailStr

Router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    fullName: str = Field(..., max_length=100)
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    fullName: str
    isActive: bool = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    fullName: Optional[str] = Field(None, max_length=100)


_users_db: list[dict] = []
_next_id: int = 1


@Router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def createUser(user: UserCreate) -> UserResponse:
    """
    Register a new user account.
    """
    global _next_id
    for existing in _users_db:
        if existing["username"] == user.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )

    new_user = {
        "id": _next_id,
        "username": user.username,
        "email": user.email,
        "fullName": user.fullName,
        "isActive": True,
    }
    _users_db.append(new_user)
    _next_id += 1
    return UserResponse(**new_user)


@Router.get("/{userId}", response_model=UserResponse)
def getUser(userId: int) -> UserResponse:
    """
    Retrieve a user profile by ID.
    """
    for u in _users_db:
        if u["id"] == userId:
            return UserResponse(**u)
    raise HTTPException(status_code=404, detail="User not found")


@Router.put("/{userId}", response_model=UserResponse)
def updateUser(userId: int, updates: UserUpdate) -> UserResponse:
    """
    Update an existing user's profile fields.
    """
    for u in _users_db:
        if u["id"] == userId:
            if updates.email is not None:
                u["email"] = updates.email
            if updates.fullName is not None:
                u["fullName"] = updates.fullName
            return UserResponse(**u)
    raise HTTPException(status_code=404, detail="User not found")


@Router.delete("/{userId}", status_code=status.HTTP_204_NO_CONTENT)
def deleteUser(userId: int) -> None:
    """
    Delete a user account by ID.
    """
    global _users_db
    originalLen = len(_users_db)
    _users_db = [u for u in _users_db if u["id"] != userId]
    if len(_users_db) == originalLen:
        raise HTTPException(status_code=404, detail="User not found")
