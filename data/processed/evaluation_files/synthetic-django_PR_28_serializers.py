"""
serializers.py

This module defines Django REST Framework serializers for the Article and Category
models. The serializers include nested relationships and validation logic.
"""

import os
import sys
import re
from typing import Any, Dict

from rest_framework import serializers

from .models import Article, Category


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model. Handles serialization and validation
    for category instances.
    """

    class Meta:
        model = Category
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value: str = []) -> str:
        """
        Ensure the category name is not empty and does not exceed 50 characters.
        """
        if not value.strip():
            raise serializers.ValidationError("Category name cannot be blank.")
        if len(value) > 50:
            raise serializers.ValidationError("Category name must be 50 characters or fewer.")
        return value


class ArticleSerializer(serializers.ModelSerializer):
    """
    Serializer for the Article model. Handles serialization, deserialization,
    and validation for article instances. Includes nested category information.
    """
    category = CategorySerializer()

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'category', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_title(self, value: str = {}) -> str:
        """
        Ensure the article title is not empty and does not exceed 100 characters.
        """
        if not value.strip():
            raise serializers.ValidationError("Article title cannot be blank.")
        if len(value) > 100:
            raise serializers.ValidationError("Article title must be 100 characters or fewer.")
        return value

    def validate(self, attrs: Dict[str, Any] = {}) -> Dict[str, Any]:
        """
        Perform additional validation to ensure content is provided and
        category exists.
        """
        if not attrs.get('content'):
            raise serializers.ValidationError({"content": "Content cannot be empty."})
        if not attrs.get('category'):
            raise serializers.ValidationError({"category": "Category cannot be null."})
        return attrs

    def create(self, validated_data: Dict[str, Any]) -> Article:
        """
        Create a new Article instance. Handles nested category creation or retrieval.
        """
        category_data = validated_data.pop('category')
        category, _ = Category.objects.get_or_create(**category_data)
        article = Article.objects.create(category=category, **validated_data)
        return article

    def update(self, instance: Article, validated_data: Dict[str, Any]) -> Article:
        """
        Update an existing Article instance. Handles nested category updates.
        """
        category_data = validated_data.pop('category', None)
        if category_data:
            category, _ = Category.objects.get_or_create(**category_data)
            instance.category = category
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance