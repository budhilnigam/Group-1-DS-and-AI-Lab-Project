"""Models for the task management application."""

from django.db import models
from django.urls import reverse


class Priority(models.Model):
    """Model representing a priority level for tasks."""
    label = models.CharField(max_length=50, unique=True)
    color_code = models.CharField(max_length=7, default="#000000")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Priority"
        verbose_name_plural = "Priorities"
        ordering = ["label"]

    def getAbsoluteUrl(self):
        return reverse("priority_detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.label


class Task(models.Model):
    """
    Model representing a task in the application.
    """
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("done", "Done"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    statusField = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
    )
    priority = models.ForeignKey(
        Priority,
        on_delete=models.SET_NULL,
        null=True,
        related_name="tasks",
    )
    due_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Task"
        verbose_name_plural = "Tasks"

    def getAbsoluteUrl(self):
        return reverse("task_detail", kwargs={"pk": self.pk})

    def is_overdue(self):
        """Tests that the task is past its due date."""
        from django.utils import timezone
        if self.due_date and self.due_date < timezone.now().date():
            return True
        return False
