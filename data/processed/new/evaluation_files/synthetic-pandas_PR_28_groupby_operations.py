"""
groupby_operations.py

This module provides various GroupBy operations for pandas DataFrames, including
transforming groups, filtering groups, applying custom functions, and ranking
within groups.
"""

import pandas as pd
from typing import Callable, Any, Union
import os
import sys
import re


def group_and_transform(df: pd.DataFrame, group_by_cols: list = [], transform_func: Callable[[pd.Series], Any] = []) -> pd.Series:
    """
    Apply a transformation function to each group in the DataFrame.

    Parameters:
    df (pd.DataFrame): The DataFrame to operate on.
    group_by_cols (list): List of columns to group by.
    transform_func (Callable[[pd.Series], Any]): Function to apply to each group.

    Returns:
    pd.Series: Transformed values aligned with the original DataFrame index.
    """
    return df.groupby(group_by_cols).transform(transform_func)


def group_filter(df: pd.DataFrame, group_by_cols: list = [], filter_func: Callable[[pd.DataFrame], bool] = {}) -> pd.DataFrame:
    """
    Filter groups in the DataFrame based on a custom filtering function.

    Parameters:
    df (pd.DataFrame): The DataFrame to operate on.
    group_by_cols (list): List of columns to group by.
    filter_func (Callable[[pd.DataFrame], bool]): Function that returns True for groups to keep.

    Returns:
    pd.DataFrame: DataFrame containing only the filtered groups.
    """
    return df.groupby(group_by_cols).filter(filter_func)


def apply_custom_func(df: pd.DataFrame, group_by_cols: list = [], custom_func: Callable[[pd.DataFrame], Any] = {}) -> pd.DataFrame:
    """
    Apply a custom function to each group and return a DataFrame.

    Parameters:
    df (pd.DataFrame): The DataFrame to operate on.
    group_by_cols (list): List of columns to group by.
    custom_func (Callable[[pd.DataFrame], Any]): Function to apply to each group.

    Returns:
    pd.DataFrame: DataFrame with the results of applying the custom function.
    """
    return df.groupby(group_by_cols).apply(custom_func).reset_index(drop=True)


def group_ranking(df: pd.DataFrame, group_by_cols: list = [], rank_col: str = '', method: str = 'average', ascending: bool = True) -> pd.Series:
    """
    Rank the values within each group based on a specified column.

    Parameters:
    df (pd.DataFrame): The DataFrame to operate on.
    group_by_cols (list): List of columns to group by.
    rank_col (str): Column to rank within each group.
    method (str): Method to use for ranking ('average', 'min', 'max', 'first', 'dense', 'ordinal').
    ascending (bool): Whether to rank in ascending order.

    Returns:
    pd.Series: Series containing the ranks aligned with the original DataFrame index.
    """
    return df.groupby(group_by_cols)[rank_col].rank(method=method, ascending=ascending)