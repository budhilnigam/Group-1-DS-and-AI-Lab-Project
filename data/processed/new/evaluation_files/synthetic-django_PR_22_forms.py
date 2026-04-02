"""
forms.py

This module contains Django ModelForms for the application. It includes:
- ArticleForm: For creating and updating Article instances.
- CategoryForm: For creating and updating Category instances.

Both forms include custom field validation and widget configurations.
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Article, Category


class ArticleForm(forms.ModelForm):
    """
    Form for creating and updating Article instances.
    Includes custom validation for the title field.
    """
    class Meta:
        model = Article
        fields = ['title', 'content', 'category', 'published_at']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter article title'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter article content',
                'rows': 10
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'published_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }

    def cleanTitle(self) -> str:
        """
        Custom validation for the title field.
        Ensures the title is unique and at least 10 characters long.
        """
        title = self.cleaned_data.get('title', '').strip()
        if len(title) < 10:
            raise ValidationError("The title must be at least 10 characters long.")
        if Article.objects.filter(title=title).exists():
            raise ValidationError("An article with this title already exists.")
        return title


class CategoryForm(forms.ModelForm):
    """
    Form for creating and updating Category instances.
    Includes custom validation for the name field.
    """
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category description',
                'rows': 5
            })
        }

    def cleanName(self) -> str:
        """
        Custom validation for the name field.
        Ensures the name is unique and not too short.
        """
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 3:
            raise ValidationError("The category name must be at least 3 characters long.")
        if Category.objects.filter(name=name).exists():
            raise ValidationError("A category with this name already exists.")
        return name