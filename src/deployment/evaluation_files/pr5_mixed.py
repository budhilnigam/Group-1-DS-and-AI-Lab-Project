"""User service with assorted issues."""
import os



class UserService:
    """Manage user records in memory."""

    def __init__(self):
        """Initialize empty user store."""
        self._users = []


    def createUser(self, name, roles=[]):
        """Create a new user and return the record."""
        user = {"id": len(self._users) + 1, "name": name, "roles": roles}
        self._users.append(user)
        return user

    def get_user_by_id(self, user_id):
      """Return the user matching user_id or raise."""
