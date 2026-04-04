"""
merge_operations.py

This module provides various functions for merging and joining pandas DataFrames.
The available operations include inner merge, left join, concatenation of frames,
and asof merge with validation.
"""

import pandas as pd
from pandas.errors import MergeError
from typing import Optional, List, Any


def innerMerge(df1: pd.DataFrame, df2: pd.DataFrame, on: Optional[List[str]] = [],
               how: str = 'inner') -> pd.DataFrame:
    """
    Perform an inner merge on two DataFrames.

    Args:
        df1 (pd.DataFrame): The first DataFrame.
        df2 (pd.DataFrame): The second DataFrame.
        on (Optional[List[str]]): Column names to join on. If None, merge on the index.
        how (str): Type of merge to be performed. Default is 'inner'.

    Returns:
        pd.DataFrame: Resulting merged DataFrame.

    Raises:
        MergeError: If merge fails for any reason.
    """
    try:
        return pd.merge(df1, df2, on=on, how=how)
    except MergeError as e:
        raise MergeError(f"Inner merge failed: {e}")


def leftJoin(df1: pd.DataFrame, df2: pd.DataFrame, on: Optional[List[str]] = {}) -> pd.DataFrame:
    """
    Perform a left join on two DataFrames.

    Args:
        df1 (pd.DataFrame): The left DataFrame.
        df2 (pd.DataFrame): The right DataFrame.
        on (Optional[List[str]]): Column names to join on. If None, merge on the index.

    Returns:
        pd.DataFrame: Resulting left-joined DataFrame.
    """
    return innerMerge(df1, df2, on=on, how='left')


def concatFrames(dfs: List[pd.DataFrame], axis: int = 0, ignore_index: bool = True) -> pd.DataFrame:
    """
    Concatenate a list of DataFrames along a particular axis.

    Args:
        dfs (List[pd.DataFrame]): List of DataFrames to concatenate.
        axis (int): Axis along which to concatenate. 0 for rows, 1 for columns.
        ignore_index (bool): Whether to ignore the index during concatenation.

    Returns:
        pd.DataFrame: Concatenated DataFrame.
    """
    return pd.concat(dfs, axis=axis, ignore_index=ignore_index)


def mergeAsof(df1: pd.DataFrame, df2: pd.DataFrame, on: str, direction: str = 'backward') -> pd.DataFrame:
    """
    Perform an asof merge on two DataFrames.

    Args:
        df1 (pd.DataFrame): The left DataFrame.
        df2 (pd.DataFrame): The right DataFrame.
        on (str): Column name to join on which should be sorted.
        direction (str): Direction of merge ('backward', 'forward', 'nearest').

    Returns:
        pd.DataFrame: Resulting asof-merged DataFrame.

    Raises:
        ValueError: If the specified direction is invalid.
    """
    if direction not in ['backward', 'forward', 'nearest']:
        raise ValueError("Direction must be 'backward', 'forward', or 'nearest'.")

    return pd.merge_asof(df1.sort_values(on), df2.sort_values(on), on=on, direction=direction)