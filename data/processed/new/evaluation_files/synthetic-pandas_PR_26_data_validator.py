"""data_validator.py

This module provides validation functions for DataFrame schema checking,
range validation, null value assertions, and unique column checks using
pandas.

Functions:
- check_schema: Validate that a DataFrame conforms to a specified schema.
- validate_ranges: Ensure that values in specified columns fall within given ranges.
- assert_no_nulls: Check for null values in specified columns or the entire DataFrame.
- check_unique_columns: Verify that specified columns contain unique values.
"""

import pandas as pd
from pandas.api.types import is_numeric_dtype
from typing import Dict, List, Tuple, Union


def check_schema(df: pd.DataFrame, schema: Dict[str, str]) -> None:
  """Check if the DataFrame columns match the specified schema.

  Args:
    df (pd.DataFrame): DataFrame to validate.
    schema (Dict[str, str]): Dictionary mapping column names to expected types.

  Raises:
    ValueError: If DataFrame does not conform to the schema.
  """
  for column, expected_type in schema.items():
    if column not in df.columns:
      raise ValueError(f"Missing column: {column}")
    actual_type = str(df[column].dtype)
    if expected_type != actual_type:
      raise ValueError(f"Column '{column}' type mismatch: expected {expected_type}, got {actual_type}")


def validateRanges(df: pd.DataFrame, column_ranges: Dict[str, Tuple[Union[int, float], Union[int, float]]]) -> None:
  """Validate that the values in specified columns fall within given ranges.

  Args:
    df (pd.DataFrame): DataFrame to validate.
    column_ranges (Dict[str, Tuple[Union[int, float], Union[int, float]]]):
      Dictionary mapping column names to (min, max) tuples.

  Raises:
    ValueError: If any value in the specified columns is out of range.
  """
  for column, (min_val, max_val) in column_ranges.items():
    if column not in df.columns:
      raise ValueError(f"Column '{column}' not found in DataFrame.")
    if not is_numeric_dtype(df[column]):
      raise ValueError(f"Column '{column}' is not numeric.")
    if not df[column].between(min_val, max_val).all():
      raise ValueError(f"Values in column '{column}' are out of the specified range [{min_val}, {max_val}].")


def assertNoNulls(df: pd.DataFrame, columns: Union[List[str], None] = None) -> None:
  """Assert that there are no null values in specified columns or the entire DataFrame.

  Args:
    df (pd.DataFrame): DataFrame to validate.
    columns (Union[List[str], None]): List of columns to check for nulls.
      If None, checks the entire DataFrame.

  Raises:
    ValueError: If any null values are found.
  """
  if columns is None:
    columns = df.columns.tolist()

  for column in columns:
    if column not in df.columns:
      raise ValueError(f"Column '{column}' not found in DataFrame.")
    if df[column].isnull().any():
      raise ValueError(f"Column '{column}' contains null values.")


def checkUniqueColumns(df: pd.DataFrame, columns: List[str]) -> None:
  """Check that specified columns contain unique values.

  Args:
    df (pd.DataFrame): DataFrame to validate.
    columns (List[str]): List of columns to check for uniqueness.

  Raises:
    ValueError: If any specified column does not contain unique values.
  """
  for column in columns:
    if column not in df.columns:
      raise ValueError(f"Column '{column}' not found in DataFrame.")
    if not df[column].is_unique:
      raise ValueError(f"Column '{column}' does not contain unique values.")