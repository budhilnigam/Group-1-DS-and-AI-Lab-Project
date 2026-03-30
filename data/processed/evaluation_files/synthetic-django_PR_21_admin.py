"""
Admin configuration for the blog application.

This module defines the ModelAdmin classes for managing models in the Django
admin interface. It includes configuration for displaying, searching, filtering,
and managing fields in the admin interface.
"""

import os
import sys
import re

from typing import Any, Optional

from django.contrib import admin
from django.db.models import QuerySet

from .models import Article


class ArticleAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Article model.
    """

    list_display = ('title', 'author', 'publication_date', 'is_published')
    search_fields = ('title', 'content', 'author__username')
    list_filter = ('is_published', 'publication_date', 'author')
    prepopulated_fields = {'slug': ('title',)}

    def get_queryset(self, request: Any) -> QuerySet:
        """
        Customize the queryset to include additional annotations or filters.

        Args:
            request (Any): The current HttpRequest object.

        Returns:
            QuerySet: The queryset for the admin interface.
        """
        qs = super().get_queryset(request)
        return qs

    def save_model(
        self, request: Any, obj: Article, form: Any, change: bool
    ) -> None:
        """
        Override the save_model method to perform additional actions during save.

        Args:
            request (Any): The current HttpRequest object.
            obj (Article): The Article instance being saved.
            form (Any): The form used to edit the instance.
            change (bool): True if the object is being changed, False if being created.
        """
        if not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def delete_model(self, request: Any, obj: Article) -> None:
        """
        Override the delete_model method to handle custom delete logic.

        Args:
            request (Any): The current HttpRequest object.
            obj (Article): The Article instance being deleted.
        """
        # Custom delete logic can be added here if needed
        super().delete_model(request, obj)

    def has_change_permission(
        self, request: Any, obj: Optional[Article] = None
    ) -> bool:
        """
        Restrict change permissions based on custom logic.

        Args:
            request (Any): The current HttpRequest object.
            obj (Optional[Article]): The Article instance being checked.

        Returns:
            bool: Whether the user has change permission.
        """
        if obj and obj.is_published:
            return False
        return super().has_change_permission(request, obj)


admin.site.register(Article, ArticleAdmin)