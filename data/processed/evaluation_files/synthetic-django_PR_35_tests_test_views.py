import os
import sys
import re
"""
Unit tests for views in the Django application.

This module contains test cases for the following views:
- Article list view
- Article detail view
- Create article view (requires login)
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from articles.models import Article


class ArticleViewsTestCase(TestCase):
    """
    Test case for views related to articles.
    """

    def setUp(self) -> None:
        """
        Set up test environment by creating test data and a test client.
        """
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', password='password123'
        )
        self.article_1 = Article.objects.create(
            title='Test Article 1',
            content='Content for article 1',
            author=self.user
        )
        self.article_2 = Article.objects.create(
            title='Test Article 2',
            content='Content for article 2',
            author=self.user
        )
        self.article_list_url = reverse('article_list')
        self.article_detail_url = reverse('article_detail', args=[self.article_1.id])
        self.create_article_url = reverse('article_create')

    def test_article_list(self) -> None:
        """
        Test that the article list view returns a 200 status code
        and contains the correct articles.
        """
        response = self.client.get(self.article_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article_1.title)
        self.assertContains(response, self.article_2.title)

    def test_article_detail(self) -> None:
        """
        Test that the article detail view returns a 200 status code
        and displays the correct article content.
        """
        response = self.client.get(self.article_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article_1.title)
        self.assertContains(response, self.article_1.content)

    def test_create_requires_login(self) -> None:
        """
        Test that the create article view requires the user to be logged in.
        """
        response = self.client.get(self.create_article_url)
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(response.status_code, 302)  # Redirect to login

        login_successful = self.client.login(username='testuser', password='password123')
        self.assertTrue(login_successful)

        response = self.client.get(self.create_article_url)
        self.assertEqual(response.status_code, 200)