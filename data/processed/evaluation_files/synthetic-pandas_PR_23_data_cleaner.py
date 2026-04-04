"""
data_cleaner.py

This module provides functions for cleaning data using pandas.
Functions include removing duplicates, standardizing column names,
fixing data types, and handling outliers using the IQR method.
"""

import pandas as pd
from typing import List, Dict, Any
import os
import sys
import re

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
  """
  Remove duplicate rows from the DataFrame.

  Args:
      df (pd.DataFrame): The input DataFrame.

  Returns:
      pd.DataFrame: A DataFrame without duplicate rows.
  """
  return df.drop_duplicates()


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
  """
  Standardize column names to lowercase and replace spaces with underscores.

  Args:
      df (pd.DataFrame): The input DataFrame.

  Returns:
      pd.DataFrame: A DataFrame with standardized column names.
  """
    df.columns = df.columns.str.lower().str.replace(' ', '_')
    return df


def fix_dtypes(df: pd.DataFrame, dtype_mapping: Dict[str, Any]) -> pd.DataFrame:
  """
  Fix the data types of specified columns in the DataFrame.

  Args:
      df (pd.DataFrame): The input DataFrame.
      dtype_mapping (Dict[str, Any]): A dictionary mapping column names to data types.

  Returns:
      pd.DataFrame: A DataFrame with corrected data types.
  """
  for column, dtype in dtype_mapping.items():
      if column in df.columns:
          df[column] = df[column].astype(dtype)
  return df


def handle_outliers(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
  """
  Handle outliers in the specified columns using the IQR method.

  Args:
      df (pd.DataFrame): The input DataFrame.
      columns (List[str]): A list of column names to check for outliers.

  Returns:
      pd.DataFrame: A DataFrame with outliers handled.
  """
    for column in columns:
        if column in df.columns:
            q1 = df[column].quantile(0.25)
            q3 = df[column].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            df[column] = df[column].clip(lower=lower_bound, upper=upper_bound)
    return df