"""Unit tests for Django forms."""

import os
import sys
import re

from django.test import TestCase
from myapp.forms import ExampleForm
from myapp.models import ExampleModel


class ExampleFormTestCase(TestCase):
  """TestCase for validating ExampleForm behavior."""

      def setUp(self) -> None:
          """Set up test data for form testing."""
          self.valid_data = {
            "title": "Unique Title",
            "description": "This is a valid description.",
          }
          self.existing_instance = ExampleModel.objects.create(
              title="Existing Title",
              description="Existing description.",
          )

    def test_valid_form(self) -> None:
        """Test that the form is valid with valid data."""
        form = ExampleForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["title"], self.valid_data["title"])
        self.assertEqual(form.cleaned_data["description"], self.valid_data["description"])

    def test_empty_form(self) -> None:
        """Test that the form is invalid with empty data."""
        form = ExampleForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("description", form.errors)

      def test_duplicate_title_validation(self) -> None:
          """Test that the form raises validation error for duplicate titles."""
          duplicate_data = {
              "title": self.existing_instance.title,
              "description": "Another description.",
          }
          form = ExampleForm(data=duplicate_data)
          self.assertFalse(form.is_valid())
          self.assertIn("title", form.errors)
          self.assertEqual(
              form.errors["title"][0],
              "An item with this title already exists."
          )