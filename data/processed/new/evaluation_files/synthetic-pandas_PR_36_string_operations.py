"""
string_operations.py

This module provides string accessor operations for pandas Series.
It includes functions to clean text, extract patterns using regular expressions,
and split columns based on specified delimiters. These functions utilize
pandas' .str methods for efficient string manipulation.
"""

import pandas as pd
import re
from typing import List, Optional, Tuple


def clean_text(series: pd.Series, to_lower: bool = True, strip: bool = True) -> pd.Series:
    """
    Clean the text in a pandas Series.

    Parameters:
        series (pd.Series): The Series containing string data to be cleaned.
        to_lower (bool): If True, convert text to lowercase. Default is True.
        strip (bool): If True, strip leading and trailing whitespace. Default is True.

    Returns:
        pd.Series: The cleaned Series.
    """
    if not pd.api.types.is_string_dtype(series):
        raise ValueError("Input series must be of string dtype.")

  cleaned_series = series.copy()

    if to_lower:
        cleaned_series = cleaned_series.str.lower()
    if strip:
      cleaned_series = cleaned_series.str.strip()

    return cleaned_series


def extractPatterns(series: pd.Series, pattern: str) -> pd.Series:
    """
    Extract patterns from a pandas Series using a regular expression.

    Parameters:
        series (pd.Series): The Series containing string data from which to extract patterns.
        pattern (str): The regular expression pattern to search for.

    Returns:
        pd.Series: A Series containing the extracted patterns or NaN if not found.
    """
    if not pd.api.types.is_string_dtype(series):
        raise ValueError("Input series must be of string dtype.")

    return series.str.extract(pattern, expand=False)


def split_columns(series: pd.Series, delimiter: str, expand: bool = True) -> pd.DataFrame:
    """
    Split a pandas Series into multiple columns based on a specified delimiter.

    Parameters:
        series (pd.Series): The Series containing string data to be split.
        delimiter (str): The delimiter to use for splitting the strings.
        expand (bool): If True, return a DataFrame with new columns. If False, return a Series of lists. Default is True.

    Returns:
        pd.DataFrame or pd.Series: DataFrame with new columns or Series of lists.
    """
    if not pd.api.types.is_string_dtype(series):
        raise ValueError("Input series must be of string dtype.")

    return series.str.split(delimiter, expand=expand)


def main() -> None:
    """
    Example main function to demonstrate the usage of the string operations.
    """
    sample_data = pd.Series([
        "  Hello World!  ",
        "Python,Java,C++",
        "foo123bar",
        "   Data Science   "
    ])

    print("Original Data:")
    print(sample_data)

    cleaned_data = clean_text(sample_data)
    print("\nCleaned Data:")
    print(cleaned_data)

    extracted_data = extractPatterns(cleaned_data, r'(\w+)')
    print("\nExtracted Data:")
    print(extracted_data)

    split_data = splitColumns(sample_data[1], ',')
    print("\nSplit Data:")
    print(split_data)


if __name__ == "__main__":
    main()