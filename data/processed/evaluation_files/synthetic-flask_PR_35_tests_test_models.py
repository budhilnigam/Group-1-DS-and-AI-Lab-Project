import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sys
import re

# Assuming User and Post models are defined in the models module
from models import User, Post

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


@pytest.fixture
def user() -> User:
    """
    Creates a User instance for testing.
    """
    user = User(username='testuser', email='test@example.com')
    user.set_password('password123')
    return user


@pytest.fixture
def post(user: User) -> Post:
    """Creates a Post instance for testing."""
    post = Post(title='Test Post', content='This is a test post.', author=user)
    return post


@pytest.fixture(autouse=True)
def setup_database() -> None:
    db.create_all()
    yield
    db.session.remove()
    db.drop_all()


def test_user_creation(user: User) -> None:
    """Test that a user can be created and stored in the database."""
    db.session.add(user)
    db.session.commit()

    assert user.id is not None
    assert user.username == 'testuser'
    assert user.email == 'test@example.com'


def test_password_hashing(user: User) -> None:
    """
    Test that the password hashing and verification works correctly.
    """
    assert user.check_password('password123') is True
    assert user.check_password('wrongpassword') is False


def test_post_relationship(user: User, post: Post) -> None:
    """Test the relationship between User and Post models."""
    db.session.add(user)
    db.session.add(post)
    db.session.commit()

    assert post.author == user
    assert user.posts.count() == 1
    assert user.posts.first().title == 'Test Post'