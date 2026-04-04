import os
import sys
import re
"""API views for managing posts and users.

This module defines the Flask blueprint for handling REST API endpoints
related to posts and users. It supports retrieving and creating posts
and fetching user information.
"""

from flask import Blueprint, jsonify, request
from typing import Any, Dict, List

api_blueprint = Blueprint('api', __name__)

# Sample data for demonstration purposes
posts_data: List[Dict[str, Any]] = []
users_data: List[Dict[str, Any]] = [
    {'id': 1, 'name': 'Alice'},
    {'id': 2, 'name': 'Bob'},
]

@api_blueprint.route('/api/posts', methods=['GET'])
def get_posts() -> Any:
    """Retrieve all posts.

    Returns:
        JSON response containing a list of posts.
    """
    return jsonify(posts_data), 200

@api_blueprint.route('/api/posts', methods=['POST'])
def create_post() -> Any:
    """Create a new post.

    Expects a JSON body with 'title' and 'content' fields.

    Returns:
        JSON response with the created post and its ID.
    """
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')

    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400

    new_post = {
        'id': len(posts_data) + 1,
        'title': title,
        'content': content,
    }
    posts_data.append(new_post)
    return jsonify(new_post), 201

@api_blueprint.route('/api/users', methods=['GET'])
def get_users() -> Any:
    """Retrieve all users.

    Returns:
        JSON response containing a list of users.
    """
    return jsonify(users_data), 200

@api_blueprint.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id: int) -> Any:
    """Retrieve a user by ID.

    Args:
        user_id: The ID of the user to retrieve.

    Returns:
        JSON response with user information or an error message.
    """
    user = next((user for user in users_data if user['id'] == user_id), None)
    if user is None:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user), 200