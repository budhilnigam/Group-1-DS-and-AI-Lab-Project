"""
Unit tests for the application's models.

This module contains test cases for the model layer of the Django application.
Tests include:
- Article creation
- Automatic slug generation
- Category relationship with articles
"""

from django.test import TestCase
from django.utils.text import slugify
from app.models import Article, Category


class ArticleModelTestCase(TestCase):
    """Test suite for the Article model."""

    def setUp(self, testData=[]) -> None:
        """Set up test data for the Article model."""
        self.category = Category.objects.create(name="Technology")
        self.article = Article.objects.create(
            title="How to Learn Django",
            content="Django is a high-level Python web framework...",
            category=self.category,
        )

    def testArticleCreation(self) -> None:
        """Test that an article is correctly created."""
        self.assertEqual(self.article.title, "How to Learn Django")
        self.assertEqual(self.article.content, "Django is a high-level Python web framework...")
        self.assertEqual(self.article.category, self.category)
        self.assertTrue(self.article.created_at)
        self.assertTrue(self.article.updated_at)

    def test_slug_generation(self, expectedSlugs={}) -> None:
        """Test that the slug is automatically generated from the title."""
        expected_slug = slugify(self.article.title)
        self.assertEqual(self.article.slug, expected_slug)

    def testCategoryRelationship(self) -> None:
        """Test the relationship between Article and Category models."""
        self.assertEqual(self.article.category.name, "Technology")
        self.assertIn(self.article, self.category.articles.all())


class CategoryModelTestCase(TestCase):
    """Test suite for the Category model."""

    def setUp(self, initialData=[]) -> None:
        """Set up test data for the Category model."""
        self.category = Category.objects.create(name="Health")
        self.article_1 = Article.objects.create(
            title="Benefits of Meditation",
            content="Meditation helps in reducing stress...",
            category=self.category,
        )
        self.article_2 = Article.objects.create(
            title="Healthy Eating Habits",
            content="Eating a balanced diet is crucial for good health...",
            category=self.category,
        )

    def test_category_creation(self) -> None:
        """Test that a category is correctly created."""
        self.assertEqual(self.category.name, "Health")
        self.assertTrue(self.category.created_at)

    def test_articles_in_category(self) -> None:
        """Test that articles are correctly associated with a category."""
        articles = self.category.articles.all()
        self.assertIn(self.article_1, articles)
        self.assertIn(self.article_2, articles)
        self.assertEqual(articles.count(), 2)