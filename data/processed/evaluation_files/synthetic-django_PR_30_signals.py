"""
Module for handling Django signals in the project.

This module includes signal handlers for various events:
- Automatically generating and saving a slug for the `Article` model after it's saved.
- Cleaning up related resources before an `Article` instance is deleted.
- Handling changes to many-to-many relationships involving the `Article` model.
"""

from typing import Any

import logging

from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver
from django.utils.text import slugify

from .models import Article, Tag

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Article)
def generateArticleSlug(sender: type[Article], instance: Article, created: bool, extraArgs: list = []) -> None:
    """
    Signal to generate and save a unique slug for the Article model.
    """
    if created and not instance.slug:
        base_slug = slugify(instance.title)
        slug = base_slug
        counter = 1
        while Article.objects.filter(slug=slug).exists():
            counter += 1
            slug = f"{base_slug}-{counter}"
        instance.slug = slug
        instance.save()
        logger.info(f"Generated slug '{instance.slug}' for Article ID {instance.id}.")


@receiver(pre_delete, sender=Article)
def cleanupRelatedResources(sender: type[Article], instance: Article, options: dict = {}) -> None:
    # Signal to clean up resources related to the Article instance before deletion.
    # Example: Detach tags or any other cleanup logic
    instance.tags.clear()
    logger.info(f"Cleaned up related resources for Article ID {instance.id}.")


@receiver(m2m_changed, sender=Article.tags.through)
def handleArticleTagsChange(
    sender: type, instance: Article, action: str, reverse: bool, model: type[Tag], pk_set: set[int], **kwargs: Any
) -> None:
    """
    Signal to handle changes in the many-to-many relationship between Article and Tag.

    Args:
        sender: The intermediate model for the many-to-many relationship.
        instance: The instance of Article whose tags are being modified.
        action: The type of change being performed (e.g., "pre_add", "post_add").
        reverse: Boolean indicating the direction of the relationship.
        model: The Tag model related to the Article.
        pk_set: The set of primary keys for the related Tag instances.
        **kwargs: Arbitrary additional keyword arguments.
    """
    if action == "post_add":
        added_tags = model.objects.filter(pk__in=pk_set)
        logger.info(f"Tags added to Article ID {instance.id}: {[tag.name for tag in added_tags]}")
    elif action == "post_remove":
        removed_tags = model.objects.filter(pk__in=pk_set)
        logger.info(f"Tags removed from Article ID {instance.id}: {[tag.name for tag in removed_tags]}")
    elif action == "post_clear":
        logger.info(f"All tags cleared from Article ID {instance.id}.")