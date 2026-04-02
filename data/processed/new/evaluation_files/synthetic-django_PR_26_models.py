"""
Django models for managing Articles, Categories, and Tags in a blogging application.
"""

from django.db import models
from django.urls import reverse


class Category(models.Model):
  """
    Model representing a category to which articles can belong.
  """
  name = models.CharField(max_length=100, unique=True)
  slug = models.SlugField(max_length=100, unique=True)
  description = models.TextField(blank=True, null=True)
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  class Meta:
      verbose_name = "Category"
      verbose_name_plural = "Categories"
      ordering = ['name']

  def __str__(self) -> str:
      return self.name

  def getAbsoluteUrl(self) -> str:
      return reverse("category_detail", kwargs={"slug": self.slug})


class Tag(models.Model):
    """
    Model representing a tag that can be assigned to articles.
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("tag_detail", kwargs={"slug": self.slug})


class Article(models.Model):
      """
      Model representing an article in the blog.
      """
      title = models.CharField(max_length=200)
      slug = models.SlugField(max_length=200, unique=True)
      content = models.TextField()
      summary = models.TextField(blank=True, null=True)
      published_at = models.DateTimeField(blank=True, null=True)
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)
      category = models.ForeignKey(
          Category,
          on_delete=models.SET_NULL,
          null=True,
          related_name="articles"
      )
      tags = models.ManyToManyField(Tag, related_name="articles", blank=True)

      class Meta:
          verbose_name = "Article"
          verbose_name_plural = "Articles"
          ordering = ['-published_at', '-created_at']

      def __str__(self) -> str:
          return self.title

      def getAbsoluteUrl(self) -> str:
          return reverse("article_detail", kwargs={"slug": self.slug})