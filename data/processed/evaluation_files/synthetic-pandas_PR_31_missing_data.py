"""
missing_data.py

This module provides functions for handling missing data in pandas DataFrames.
It includes functionalities to detect missing values, apply filling strategies,
interpolate missing values, and drop incomplete rows or columns.
"""

import os
import sys
import re
import pandas as pd
import numpy as np
from typing import Optional, Union, List


def detect_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect missing values in the DataFrame.

    Parameters:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: A DataFrame indicating the presence of missing values.
    """
    return df.isnull()


def fill_strategies(df: pd.DataFrame, strategy: str = 'mean', value: Optional[Union[int, float]] = None) -> pd.DataFrame:
    """
    Fill missing values in the DataFrame using specified strategy.

    Parameters:
        df (pd.DataFrame): The input DataFrame.
        strategy (str): The filling strategy ('mean', 'median', 'mode', 'constant').
        value (Optional[Union[int, float]]): A constant value to fill if strategy is 'constant'.

    Returns:
        pd.DataFrame: DataFrame with missing values filled.
    """
    if strategy == 'mean':
        return df.fillna(df.mean())
    elif strategy == 'median':
        return df.fillna(df.median())
    elif strategy == 'mode':
        return df.fillna(df.mode().iloc[0])
    elif strategy == 'constant' and value is not None:
        return df.fillna(value)
    else:
        raise ValueError("Invalid strategy. Choose from 'mean', 'median', 'mode', or 'constant'.")


def interpolate_values(df: pd.DataFrame, method: str = 'linear') -> pd.DataFrame:
    """
    Interpolate missing values in the DataFrame.

    Parameters:
        df (pd.DataFrame): The input DataFrame.
        method (str): The interpolation method (e.g., 'linear', 'time', 'polynomial').

    Returns:
        pd.DataFrame: DataFrame with interpolated values.
    """
    return df.interpolate(method=method)


def drop_incomplete(df: pd.DataFrame, axis: int = 0, thresh: Optional[int] = None) -> pd.DataFrame:
    """
    Drop rows or columns with missing values from the DataFrame.

    Parameters:
        df (pd.DataFrame): The input DataFrame.
        axis (int): The axis to drop along (0 for rows, 1 for columns).
        thresh (Optional[int]): Require that many non-NA values to keep the row/column.

    Returns:
        pd.DataFrame: DataFrame with incomplete rows/columns dropped.
    """
    return df.dropna(axis=axis, thresh=thresh) if thresh is not None else df.dropna(axis=axis)