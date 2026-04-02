"""Forms for user authentication using WTForms.

This module includes the LoginForm and RegistrationForm classes,
which define the fields and validators required for user login
and registration processes.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo


class LoginForm(FlaskForm):
    """Form for user login."""

    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    """Form for user registration."""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField('Register')

    def __init__(self, *args, **kwargs):
        """Initialize RegistrationForm with optional defaults."""
        super().__init__(*args, **kwargs)
        self.default_data = kwargs.get('default_data', {})

    def validate_username(self, field):
        """Validate the username field."""
        if not field.data:
            raise ValueError('Username is required.')
        # Assume some validation logic here

    def validate_email(self, field):
        """Validate the email field."""
        if not field.data:
            raise ValueError('Email is required.')
        # Assume some validation logic here