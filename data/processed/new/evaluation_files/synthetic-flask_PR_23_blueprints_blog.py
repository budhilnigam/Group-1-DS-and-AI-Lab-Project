import os
import sys
import re
from flask import Blueprint, request, jsonify, abort
from typing import List, Dict, Any

blog_bp = Blueprint('blog', __name__)

# In-memory storage for blog posts (for demonstration purposes)
posts: List[Dict[str, Any]] = []
post_id_counter = 1


@blog_bp.route('/posts', methods=['GET'])
def list_posts() -> jsonify:
  """Retrieve a list of all blog posts."""
  return jsonify(posts), 200


@blog_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id: int) -> jsonify:
      """Retrieve a single blog post by its ID."""
      post = next((post for post in posts if post['id'] == post_id), None)
      if post is None:
          abort(404, description="Post not found")
      return jsonify(post), 200


@blog_bp.route('/posts', methods=['POST'])
def create_post() -> jsonify:
      """Create a new blog post."""
      global post_id_counter
      data = request.get_json()
      if not data or 'title' not in data or 'content' not in data:
          abort(400, description="Invalid data")

      new_post = {
          'id': post_id_counter,
          'title': data['title'],
          'content': data['content']
      }
      posts.append(new_post)
      post_id_counter += 1
      return jsonify(new_post), 201


@blog_bp.route('/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id: int) -> jsonify:
      """Update an existing blog post by its ID."""
      data = request.get_json()
      post = next((post for post in posts if post['id'] == post_id), None)
      if post is None:
          abort(404, description="Post not found")

      if 'title' in data:
          post['title'] = data['title']
      if 'content' in data:
          post['content'] = data['content']

      return jsonify(post), 200


@blog_bp.route('/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id: int) -> jsonify:
      """Delete a blog post by its ID."""
      global posts
      posts = [post for post in posts if post['id'] != post_id]
      return jsonify({"message": "Post deleted"}), 204