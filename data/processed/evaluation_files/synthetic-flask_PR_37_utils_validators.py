"""
utils/validators.py

This module provides custom validators for validating user input, including
username validation, email domain validation, and file extension validation.
"""

import re
from typing import List


def validate_username(username: str) -> bool:
    """Validate the username for specific criteria.

    The username must be between 3 and 20 characters long and can only
    contain alphanumeric characters and underscores.

    Args:
        username (str): The username to validate.

    Returns:
        bool: True if the username is valid, False otherwise.
    """
    if not (3 <= len(username) <= 20):
        return False
    if not re.match(r'^\w+$', username):
        return False
    return True


def validate_email_domain(email: str, allowed_domains: List[str]) -> bool:
    """Validate the email domain against allowed domains.

    The function checks if the email's domain is in the list of allowed
    domains.

    Args:
        email (str): The email address to validate.
        allowed_domains (List[str]): A list of allowed email domains.

    Returns:
        bool: True if the email domain is valid, False otherwise.
    """
    try:
        domain = email.split('@')[1]
    except IndexError:
        return False
    return domain in allowed_domains


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """Validate the file extension against allowed extensions.

    The function checks if the file's extension is in the list of allowed
    extensions.

    Args:
        filename (str): The name of the file to validate.
        allowed_extensions (List[str]): A list of allowed file extensions.

    Returns:
        bool: True if the file extension is valid, False otherwise.
    """
    if '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions


def main() -> None:
    """Run some basic tests for the validators.
    """
    print("Username Validation Tests:")
    print(validate_username("valid_user"))  # True
    print(validate_username("us"))           # False
    print(validate_username("user!@#"))      # False

    print("\nEmail Domain Validation Tests:")
    print(validate_email_domain("user@example.com", ["example.com", "test.com"]))  # True
    print(validate_email_domain("user@invalid.com", ["example.com", "test.com"]))  # False

    print("\nFile Extension Validation Tests:")
    print(validate_file_extension("document.pdf", ["pdf", "docx"]))  # True
    print(validate_file_extension("image.jpg", ["png", "gif"]))      # False


if __name__ == "__main__":
    main()