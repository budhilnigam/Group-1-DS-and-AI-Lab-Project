"""
aggregations.py

This module provides various aggregation functions for pandas DataFrames.
Functions include summary statistics, grouped aggregations, and custom
aggregations using named aggregation syntax.
"""

import pandas as pd
import os
import sys
import re
from typing import Dict, Any, Optional, List


def summary_stats(df: pd.DataFrame, numeric_cols: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Calculate summary statistics for the specified numeric columns in a DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame.
        numeric_cols (Optional[List[str]]): List of numeric column names to summarize.
            If None, all numeric columns will be used.

    Returns:
        pd.DataFrame: A DataFrame containing summary statistics.
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include='number').columns.tolist()

    return df[numeric_cols].describe()


def grouped_agg(df: pd.DataFrame, group_by: List[str], agg_funcs: Dict[str, Any]) -> pd.DataFrame:
    """
    Perform grouped aggregation on a DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame.
        group_by (List[str]): List of column names to group by.
        agg_funcs (Dict[str, Any]): Dictionary specifying aggregation functions.

    Returns:
        pd.DataFrame: A DataFrame containing the aggregated results.
    """
    return df.groupby(group_by).agg(agg_funcs).reset_index()


def custom_agg(df: pd.DataFrame, group_by: List[str], **agg_kwargs: Dict[str, Any]) -> pd.DataFrame:
    """
    Perform custom aggregation on a DataFrame using named aggregation syntax.

    Args:
        df (pd.DataFrame): The input DataFrame.
        group_by (List[str]): List of column names to group by.
        **agg_kwargs (Dict[str, Any]): Named aggregation functions.

    Returns:
        pd.DataFrame: A DataFrame containing the aggregated results.
    """
    return df.groupby(group_by).agg(**agg_kwargs).reset_index()