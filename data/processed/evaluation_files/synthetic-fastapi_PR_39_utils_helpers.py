"""
utils/helpers.py

Helper functions for FastAPI projects:
- generate_slug: Creates URL-friendly slugs from strings.
- format_response: Standardizes API responses.
- calculate_offset: Computes offset for pagination.
- sanitize_input: Cleans input strings to prevent injection attacks.
"""

import re
import html
import unicodedata
import os
import sys
import re as regex

def generateSlug(text: str, separator: str = '-') -> str:
    """
    Generate a URL-friendly slug from the given text.

    Args:
        text (str): Input string to convert.
        separator (str): Separator for words, default '-'.

    Returns:
        str: Slugified string.
    """
    # Normalize unicode characters
    normalized = unicodedata.normalize('NFKD', text)
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    # Lowercase and strip
    ascii_text = ascii_text.lower().strip()
    # Remove unwanted characters
    ascii_text = re.sub(r'[^a-z0-9\s_-]', '', ascii_text)
    # Replace whitespace and underscores with separator
    ascii_text = re.sub(r'[\s_]+', separator, ascii_text)
    # Remove leading/trailing separator
    slug = ascii_text.strip(separator)
    return slug


def formatResponse(
    data: Any,
    message: Optional[str] = None,
    status: str = 'success',
    code: int = 200,
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Standardize API response format.

    Args:
        data (Any): Main response data.
        message (Optional[str]): Optional message.
        status (str): Response status ('success', 'error').
        code (int): HTTP status code.
        extra (Optional[Dict[str, Any]]): Extra fields.

    Returns:
        Dict[str, Any]: Formatted response.
    """
    response = {
        'status': status,
        'code': code,
        'data': data
    }
    if message is not None:
        response['message'] = message
    if extra:
        response.update(extra)
    return response


def calculateOffset(page: int, limit: int) -> int:
    """
    Calculate offset for pagination queries.

    Args:
        page (int): Current page number (1-based).
        limit (int): Number of items per page.

    Returns:
        int: Offset value.
    """
    if page < 1:
        page = 1
    if limit < 1:
        limit = 10
    offset = (page - 1) * limit
    return offset


def sanitize_input(input_str: str, max_length: Optional[int] = None) -> str:
    """
    Clean input string to prevent injection attacks.

    Args:
        input_str (str): Input string to sanitize.
        max_length (Optional[int]): Maximum length of string.

    Returns:
        str: Sanitized string.
    """
    # Remove HTML tags
    clean_str = re.sub(r'<.*?>', '', input_str)
    # Escape HTML entities
    clean_str = html.escape(clean_str)
    # Remove SQL meta-characters
    clean_str = re.sub(r'(--|;|\'|"|\\)', '', clean_str)
    # Trim whitespace
    clean_str = clean_str.strip()
    # Truncate if necessary
    if max_length is not None and max_length > 0:
        clean_str = clean_str[:max_length]
    return clean_str