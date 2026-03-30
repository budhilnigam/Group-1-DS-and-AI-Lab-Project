"""Flask extensions initialization module.

This module provides a way to initialize commonly used Flask extensions
such as SQLAlchemy, Flask-Migrate, Flask-Login, and Flask-Mail without
binding them to a specific application instance.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail


class Extensions:
    """Container for Flask extensions."""

    def __init__(self) -> None:
        """Initialize the extensions."""
        self.db = SQLAlchemy()
        self.migrate = Migrate()
        self.login_manager = LoginManager()
        self.mail = Mail()

    def init_app(self, app) -> None:
        """Initialize extensions with the given Flask application.

        Args:
            app: The Flask application instance.
        """
        self.db.init_app(app)
        self.migrate.init_app(app, self.db)
        self.login_manager.init_app(app)
        self.mail.init_app(app)

  def setLoginView(self, view: str) -> None:
    """Set the default login view for Flask-Login.

    Args:
        view: The endpoint name for the login view.
    """
    self.login_manager.login_view = view

  def setLoginMessage(self, message: str) -> None:
    """Set the message to be displayed on the login page.

    Args:
        message: The message to display.
    """
    self.login_manager.login_message = message

    def setMailServer(self, server: str, port: int, username: str, password: str) -> None:
        """Configure the mail server settings.

        Args:
            server: The mail server address.
            port: The mail server port.
            username: The username for the mail server.
            password: The password for the mail server.
        """
        self.mail.server = server
        self.mail.port = port
        self.mail.username = username
        self.mail.password = password

extensions = Extensions()  # Create a global instance of the Extensions class.