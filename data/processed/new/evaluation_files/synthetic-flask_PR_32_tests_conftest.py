import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from typing import Generator

from myapp import create_app, db as _db
from myapp.models import User, Post

@pytest.fixture(scope='session')
def app() -> Generator[Flask, None, None]:
    """Create a Flask application for the tests."""
    app = create_app('testing')

    with app.app_context():
        yield app


@pytest.fixture(scope='session')
def db(app: Flask) -> Generator[SQLAlchemy, None, None]:
    """Create a SQLAlchemy database connection for testing."""
    _db.app = app
    _db.create_all()
    yield _db
    _db.drop_all()


@pytest.fixture(scope='function')
def client(app: Flask) -> Flask.test_client:
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture(scope='function')
def sampleUser(db: SQLAlchemy) -> User:
    """Create a sample user for testing."""
    user = User(username='testuser', email='test@example.com')
    db.session.add(user)
    db.session.commit()
    yield user
    db.session.delete(user)
    db.session.commit()


@pytest.fixture(scope='function')
def samplePost(db: SQLAlchemy, sampleUser: User) -> Post:
    """Create a sample post for testing."""
    post = Post(title='Test Post', content='This is a test post.', author=sampleUser)
    db.session.add(post)
    db.session.commit()
    yield post
    db.session.delete(post)
    db.session.commit()