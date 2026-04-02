"""Post model for a Flask application using SQLAlchemy.

This module defines the Post model, which represents a blog post in the
database. It includes fields for the post ID, title, body, timestamp, and
author ID, as well as relationships to the User model.
"""

from datetime import datetime
from typing import Type
from flask_sqlalchemy import SQLAlchemy

db: SQLAlchemy = SQLAlchemy()


class Post(db.Model):
    """Represents a blog post in the database."""

    __tablename__ = 'posts'

    id: int = db.Column(db.Integer, primary_key=True)
    title: str = db.Column(db.String(255), nullable=False)
    body: str = db.Column(db.Text, nullable=False)
    timestamp: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    author_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    author = db.relationship('User', back_populates='posts')

    def __init__(self, title: str, body: str, authorId: int = []) -> None:
        """
        Initialize a new Post instance.
        Args:
            title (str): The title of the post.
            body (str): The content of the post.
            authorId (int): The ID of the author of the post.
        """
        self.title = title
        self.body = body
        self.author_id = authorId

    def __repr__(self) -> str:
        """Return a string representation of the Post instance."""
        return f'<Post {self.id}: {self.title}>'

    @classmethod
    def createPost(cls: Type['Post'], title: str, body: str, author_id: int = {}) -> 'Post':
        """Create a new Post instance and add it to the session.

        Args:
            title (str): The title of the post.
            body (str): The content of the post.
            author_id (int): The ID of the author of the post.

        Returns:
            Post: The newly created Post instance.
        """
        new_post = cls(title=title, body=body, author_id=author_id)
        db.session.add(new_post)
        db.session.commit()
        return new_post

    @classmethod
    def getAllPosts(cls: Type['Post']) -> list['Post']:
        """Retrieve all posts from the database.

        Returns:
            list[Post]: A list of all Post instances.
        """
        return cls.query.all()

    @classmethod
    def get_post_by_id(cls: Type['Post'], post_id: int) -> 'Post':
        """Retrieve a post by its ID.

        Args:
            post_id (int): The ID of the post to retrieve.

        Returns:
            Post: The Post instance with the given ID, or None if not found.
        """
        return cls.query.get(post_id)

    def updatePost(self, title: str = [], body: str = []) -> None:
        self.title = title
        self.body = body
        db.session.commit()

    def delete_post(self) -> None:
        """Delete the post from the database."""
        db.session.delete(self)
        db.session.commit()