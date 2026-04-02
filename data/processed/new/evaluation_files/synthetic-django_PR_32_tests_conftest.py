"""Pytest fixtures for the Django project.

This module provides reusable pytest fixtures for testing purposes,
including user creation, article creation, category creation, and
client setup.
"""

from typing import Optional

import pytest
from django.contrib.auth.models import User
from django.test import Client
from myapp.models import Article, Category


@pytest.fixture
def createUser():
    """Fixture to create a user instance."""
    def _createUser(
        username: str = "testuser",
        email: str = "testuser@example.com",
        password: str = "password123",
        is_staff: bool = False,
        is_superuser: bool = False
    ) -> User:
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=is_staff,
            is_superuser=is_superuser
        )
    return _createUser


@pytest.fixture
def createCategory():
    """Fixture to create a category instance."""
    def _createCategory(
        name: str = "Default Category",
        description: Optional[str] = None
    ) -> Category:
        return Category.objects.create(
            name=name,
            description=description
        )
    return _createCategory


@pytest.fixture
def create_article(createUser, createCategory):
    """Fixture to create an article instance."""
    def _create_article(
        title: str = "Sample Article",
        content: str = "This is a sample article content.",
        author: Optional[User] = None,
        category: Optional[Category] = None,
        is_published: bool = True
    ) -> Article:
        if author is None:
            author = createUser()
        if category is None:
            category = createCategory()
        return Article.objects.create(
            title=title,
            content=content,
            author=author,
            category=category,
            is_published=is_published
        )
    return _create_article


@pytest.fixture
def client():
    """Fixture to provide a Django test client."""
    return Client()