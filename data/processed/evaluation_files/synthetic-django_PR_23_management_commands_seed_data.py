"""
Custom Django management command to seed the database with sample data.
This command creates sample users, categories, and articles for testing or
development purposes.

Usage:
    python manage.py seed_data
"""

import random
import os
import sys
import re
from typing import Any

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from myapp.models import Category, Article


class Command(BaseCommand):
    help = "Seed the database with sample users, categories, and articles."

  def handle(self, *args: Any, **options: Any) -> None:
      self.stdout.write("Starting database seeding...")

      self.create_sample_users()
      self.create_sample_categories()
      self.create_sample_articles()

      self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))

    def create_sample_users(self) -> None:
      """
      Create sample users for the application.
      """
      usernames = ["alice", "bob", "charlie", "dave", "eve"]

      for username in usernames:
          if not User.objects.filter(username=username).exists():
              User.objects.create_user(
                  username=username,
                  email=f"{username}@example.com",
                  password="password123"
              )
              self.stdout.write(f"Created user: {username}")

    def create_sample_categories(self) -> None:
        """
        Create sample categories for the application.
        """
        category_names = ["Technology", "Health", "Science", "Travel", "Food"]

        for name in category_names:
            if not Category.objects.filter(name=name).exists():
                Category.objects.create(name=name)
                self.stdout.write(f"Created category: {name}")

    def create_sample_articles(self) -> None:
      """
      Create sample articles with random users and categories.
      """
      titles = [
          "The Future of AI",
          "10 Tips for Healthy Living",
          "Exploring the Universe",
          "Top Travel Destinations",
          "Delicious Recipes to Try"
      ]
      content = (
          "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
          "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
      )

      users = list(User.objects.all())
      categories = list(Category.objects.all())

      if not users or not categories:
          self.stdout.write(self.style.WARNING("Skipping article creation due to missing users or categories."))
          return

      for title in titles:
          category = random.choice(categories)
          author = random.choice(users)

          if not Article.objects.filter(title=title).exists():
              Article.objects.create(
                  title=title,
                  content=content,
                  author=author,
                  category=category
              )
              self.stdout.write(f"Created article: {title}")