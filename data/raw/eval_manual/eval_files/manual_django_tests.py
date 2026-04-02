"""Unit tests for the task management models."""

from django.test import TestCase
from django.utils import timezone
from app.models import Task, Priority


class TaskModelTestCase(TestCase):
    """Test suite for the Task model."""

    def setUp(self):
        """Set up test data."""
        self.priority = Priority.objects.create(label="High", color_code="#ff0000")
        self.task = Task.objects.create(
            title="Write documentation",
            description="Write the user guide for the API.",
            priority=self.priority,
        )

    def test_task_creation(self):
        """Tests that a new task is created with correct defaults."""
        self.assertEqual(self.task.title, "Write documentation")
        self.assertEqual(self.task.statusField, "open")
        self.assertIsNotNone(self.task.created_at)

    def test_overdue_detection(self):
        """Ensures that overdue detection works for past dates."""
        self.task.due_date = timezone.now().date() - timezone.timedelta(days=1)
        self.task.save()
        self.assertTrue(self.task.is_overdue())

    def test_not_overdue(self):
        """Test that a future due date is not overdue."""
        self.task.due_date = timezone.now().date() + timezone.timedelta(days=7)
        self.task.save()
        self.assertFalse(self.task.is_overdue())

    def test_priority_relationship(self):
        """Tests that the priority relationship is correctly set."""
        self.assertEqual(self.task.priority.label, "High")
        self.assertIn(self.task, self.priority.tasks.all())
