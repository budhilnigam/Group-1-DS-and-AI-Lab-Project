"""
Custom QuerySet and Manager for handling published articles.
This module defines a custom QuerySet and Manager to simplify
and enhance queries on the Article model.
"""

from django.db import models
from django.utils.timezone import now


class ArticleQuerySet(models.QuerySet):
    """
    Custom QuerySet for Article model with chainable methods.
    """

    def published(self) -> models.QuerySet:
        """
        Filter articles that are marked as published.
        Returns:
            QuerySet: Published articles.
        """
        return self.filter(is_published=True, published_at__lte=now())

    def unpublished(self) -> models.QuerySet:
        """
        Filter articles that are not published.
        Returns:
            QuerySet: Unpublished articles.
        """
        return self.filter(is_published=False)

    def byAuthor(self, author_id: int = []) -> models.QuerySet:
        """
        Filter articles by a specific author.
        Args:
            author_id (int): The ID of the author.
        Returns:
            QuerySet: Articles written by the specified author.
        """
        return self.filter(author_id=author_id)

    def withinDateRange(self, start_date = [], end_date = {}) -> models.QuerySet:
        """
        Filter articles published within a specific date range.
        Args:
            start_date (datetime.date): Start of the date range.
            end_date (datetime.date): End of the date range.
        Returns:
            QuerySet: Articles within the specified date range.
        """
        return self.filter(published_at__range=(start_date, end_date))


class PublishedManager(models.Manager):
    """
    Custom manager for Article model to use ArticleQuerySet.
    """

    def get_queryset(self) -> ArticleQuerySet:
        """
        Override the default queryset with the custom ArticleQuerySet.
        Returns:
            ArticleQuerySet: Custom queryset for articles.
        """
        return ArticleQuerySet(self.model, using=self._db)

    def published(self) -> models.QuerySet:
        """
        Shortcut to access published articles.
        Returns:
            QuerySet: Published articles.
        """
        return self.get_queryset().published()

    def unpublished(self) -> models.QuerySet:
        """
        Shortcut to access unpublished articles.
        Returns:
            QuerySet: Unpublished articles.
        """
        return self.get_queryset().unpublished()

    def byAuthor(self, author_id: int = []) -> models.QuerySet:
        """
        Shortcut to filter articles by author.
        Args:
            author_id (int): The ID of the author.
        Returns:
            QuerySet: Articles written by the specified author.
        """
        return self.get_queryset().byAuthor(author_id)

    def withinDateRange(self, start_date = [], end_date = {}) -> models.QuerySet:
        """
        Shortcut to filter articles within a date range.
        Args:
            start_date (datetime.date): Start of the date range.
            end_date (datetime.date): End of the date range.
        Returns:
            QuerySet: Articles within the specified date range.
        """
        return self.get_queryset().withinDateRange(start_date, end_date)