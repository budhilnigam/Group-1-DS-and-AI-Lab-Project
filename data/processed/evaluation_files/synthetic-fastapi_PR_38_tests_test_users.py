"""
Pytest test suite for user endpoints in the FastAPI project.

Covers:
    - User creation
    - User retrieval
    - User update
    - Listing users

Assumes the FastAPI app is imported as 'app' and endpoints are at '/users'.
"""

from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from app.main import app

import os
import sys
import re

client = TestClient(app)


@pytest.fixture
def sample_user_payload() -> Dict[str, Any]:
    """Return a sample payload for creating a user."""
    return {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "securepassword123"
    }


@pytest.fixture
def create_sample_user(sample_user_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a sample user and return the response JSON."""
    response = client.post("/users/", json=sample_user_payload)
    assert response.status_code == 201
    return response.json()


def test_create_user(sample_user_payload: Dict[str, Any]) -> None:
    """Test user creation endpoint."""
    response = client.post("/users/", json=sample_user_payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["username"] == sample_user_payload["username"]
    assert data["email"] == sample_user_payload["email"]


def test_get_user(create_sample_user: Dict[str, Any]) -> None:
    """Test retrieving a user by ID."""
    user_id = create_sample_user["id"]
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["username"] == create_sample_user["username"]
    assert data["email"] == create_sample_user["email"]


def test_update_user(create_sample_user: Dict[str, Any]) -> None:
    """Test updating a user's information."""
    user_id = create_sample_user["id"]
    update_payload = {
        "username": "jane_doe",
        "email": "jane@example.com"
    }
    response = client.put(f"/users/{user_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["username"] == update_payload["username"]
    assert data["email"] == update_payload["email"]

    # Fetch again to verify update
    get_response = client.get(f"/users/{user_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["username"] == update_payload["username"]
    assert get_data["email"] == update_payload["email"]


def test_list_users(create_sample_user: Dict[str, Any]) -> None:
    """Test listing all users."""
    response = client.get("/users/")
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert any(user["id"] == create_sample_user["id"] for user in users)


def test_get_user_not_found() -> None:
    """Test retrieval of a non-existent user returns 404."""
    response = client.get("/users/999999")
    assert response.status_code == 404


def test_create_user_invalid_payload() -> None:
    """Test user creation with invalid payload returns 422."""
    invalid_payload = {
        "username": "",
        "email": "not-an-email",
        # missing password
    }
    response = client.post("/users/", json=invalid_payload)
    assert response.status_code == 422