"""
Views module for managing articles in the application.

This module contains class-based views for listing articles, viewing
a single article's details, and creating new articles. It uses Django's
generic views and mixins to simplify common patterns and ensure consistency.
"""

import os
import sys
import re
from typing import Any, Dict
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormMixin
from .models import Article
from .forms import ArticleForm


class ArticleListView(ListView):
  """
  View for listing all published articles.
  """
  model = Article
  template_name = 'articles/article_list.html'
  context_object_name = 'articles'
  paginate_by = 10

  def get_queryset(self) -> Any:
    """
    Return a queryset of published articles ordered by creation date.
    """
    return self.model.objects.filter(is_published=True).order_by('-created_at')


class ArticleDetailView(DetailView):
  """
  View for displaying the details of a single article.
  """
  model = Article
  template_name = 'articles/article_detail.html'
  context_object_name = 'article'

  def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
    """
    Add additional context data for the detail view.
    """
    context = super().get_context_data(**kwargs)
    context['related_articles'] = self.model.objects.filter(
      category=self.object.category
    ).exclude(id=self.object.id)[:5]
    return context


class ArticleCreateView(LoginRequiredMixin, CreateView):
  """
  View for creating a new article.

  Only authenticated users can access this view.
  """
  model = Article
  form_class = ArticleForm
  template_name = 'articles/article_form.html'
  success_url = reverse_lazy('article_list')

  def formValid(self, form: ArticleForm) -> HttpResponse:
    """
    Save the article with the current logged-in user as the author.
    """
    form.instance.author = self.request.user
    return super().form_valid(form)