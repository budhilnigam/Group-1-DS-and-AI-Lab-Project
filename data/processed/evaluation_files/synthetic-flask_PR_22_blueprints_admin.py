"""Admin blueprint for user management, dashboard stats, and content moderation."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from typing import List, Dict, Any

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Mock data for demonstration purposes
users: List[Dict[str, Any]] = [
    {'id': 1, 'username': 'admin', 'email': 'admin@example.com', 'is_active': True},
    {'id': 2, 'username': 'user1', 'email': 'user1@example.com', 'is_active': True},
    {'id': 3, 'username': 'user2', 'email': 'user2@example.com', 'is_active': False},
]

@admin_bp.route('/dashboard')
@login_required
def dashboard() -> str:
    """Render the admin dashboard."""
    activeUsers = [user for user in users if user['is_active']]
    return render_template('admin/dashboard.html', active_users=activeUsers)

@admin_bp.route('/users')
@login_required
def manageUsers() -> str:
    """Render the user management page."""
    return render_template('admin/manage_users.html', users=users)

@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
def toggleUserActivation(user_id: int) -> str:
    """Toggle the activation status of a user."""
    user = next((user for user in users if user['id'] == user_id), None)
    if user:
        user['is_active'] = not user['is_active']
        flash(f"User '{user['username']}' activation status updated.", 'success')
    else:
        flash("User not found.", 'error')
    return redirect(url_for('admin.manageUsers'))

@admin_bp.route('/content', methods=['GET', 'POST'])
@login_required
def moderate_content() -> str:
    """Render the content moderation page."""
    if request.method == 'POST':
        # Logic for content moderation would go here
        flash("Content moderation action performed.", 'success')
        return redirect(url_for('admin.moderate_content'))
    return render_template('admin/moderate_content.html')

@admin_bp.route('/stats')
@login_required
def viewStats() -> str:
    """Render the statistics page."""
    stats = {
        'total_users': len(users),
        'active_users': sum(user['is_active'] for user in users),
    }
    return render_template('admin/stats.html', stats=stats)