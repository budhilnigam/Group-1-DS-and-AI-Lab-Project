import os
import sys
import re
import pytest
from flask import Flask
from flask.testing import FlaskClient

from your_flask_app import create_app, db
from your_flask_app.models import User


@pytest.fixture
def app() -> Flask:
  """Create a Flask app instance for testing."""
  app = create_app('testing')

      with app.app_context():
          db.create_all()
          yield app
          db.drop_all()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create a test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def create_user() -> User:
      """Create a user for testing purposes."""
      user = User(username='testuser', email='test@example.com')
      user.set_password('password')
      return user


def test_register(client: FlaskClient, create_user: User) -> None:
    """Test user registration endpoint."""
    response = client.post('/register', json={
        'username': create_user.username,
        'email': create_user.email,
        'password': 'password'
    })

    assert response.status_code == 201
    assert response.json['message'] == 'User registered successfully'


def test_login(client: FlaskClient, create_user: User) -> None:
    """Test user login endpoint."""
    client.post('/register', json={
        'username': create_user.username,
        'email': create_user.email,
        'password': 'password'
    })

    response = client.post('/login', json={
        'username': create_user.username,
        'password': 'password'
    })

    assert response.status_code == 200
    assert response.json['message'] == 'Login successful'
    assert 'access_token' in response.json


def test_invalid_login(client: FlaskClient) -> None:
    """Test login with invalid credentials."""
    response = client.post('/login', json={
        'username': 'invaliduser',
        'password': 'wrongpassword'
    })

    assert response.status_code == 401
    assert response.json['message'] == 'Invalid credentials'


def test_logout(client: FlaskClient, create_user: User) -> None:
    """Test user logout endpoint."""
    client.post('/register', json={
        'username': create_user.username,
        'email': create_user.email,
        'password': 'password'
    })

    login_response = client.post('/login', json={
        'username': create_user.username,
        'password': 'password'
    })

    access_token = login_response.json['access_token']
    response = client.post('/logout', headers={
        'Authorization': f'Bearer {access_token}'
    })

    assert response.status_code == 200
    assert response.json['message'] == 'Logout successful'