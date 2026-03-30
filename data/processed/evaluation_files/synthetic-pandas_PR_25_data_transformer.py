"""data_transformer.py

This module provides a set of functions for transforming pandas DataFrames.
The available transformations include melt, pivot, stack, unstack, and transpose,
with proper handling of DataFrame indices.
"""

import pandas as pd
from pandas import DataFrame
import os
import sys
import re


def melt_dataframe(df: DataFrame, id_vars: list, value_vars: list) -> DataFrame:
    """Melt a DataFrame from wide to long format.

    Args:
        df (DataFrame): The DataFrame to melt.
        id_vars (list): Column(s) to use as identifier variables.
        value_vars (list): Column(s) to unpivot.

    Returns:
        DataFrame: A melted DataFrame.
    """
    return pd.melt(df, id_vars=id_vars, value_vars=value_vars)


def pivot_dataframe(df: DataFrame, index: list, columns: str, values: str) -> DataFrame:
    """Pivot a DataFrame from long to wide format.

    Args:
        df (DataFrame): The DataFrame to pivot.
        index (list): Column(s) to use as index.
        columns (str): Column to use to make new frame's columns.
        values (str): Column(s) to use for populating new frame's values.

    Returns:
        DataFrame: A pivoted DataFrame.
    """
    return df.pivot(index=index, columns=columns, values=values)


def stack_dataframe(df: DataFrame) -> DataFrame:
    """Stack the DataFrame, turning columns into rows.

    Args:
        df (DataFrame): The DataFrame to stack.

    Returns:
        DataFrame: A stacked DataFrame.
    """
    return df.stack()


def unstack_dataframe(df: DataFrame) -> DataFrame:
    """Unstack the DataFrame, turning rows into columns.

    Args:
        df (DataFrame): The DataFrame to unstack.

    Returns:
        DataFrame: An unstacked DataFrame.
    """
    return df.unstack()


def transpose_dataframe(df: DataFrame) -> DataFrame:
    """Transpose the DataFrame, swapping rows and columns.

    Args:
        df (DataFrame): The DataFrame to transpose.

    Returns:
        DataFrame: A transposed DataFrame.
    """
    return df.T


def reset_index(df: DataFrame, drop: bool = False) -> DataFrame:
    """Reset the index of the DataFrame.

    Args:
        df (DataFrame): The DataFrame whose index is to be reset.
        drop (bool): Whether to drop the index or not.

    Returns:
        DataFrame: A DataFrame with reset index.
    """
    return df.reset_index(drop=drop)


def set_index(df: DataFrame, keys: list) -> DataFrame:
    """Set the DataFrame index using the specified keys.

    Args:
        df (DataFrame): The DataFrame whose index is to be set.
        keys (list): Column(s) to set as index.

    Returns:
        DataFrame: A DataFrame with the specified index set.
    """
    return df.set_index(keys)


def rename_columns(df: DataFrame, mapper: dict) -> DataFrame:
    """Rename columns in the DataFrame.

    Args:
        df (DataFrame): The DataFrame whose columns are to be renamed.
        mapper (dict): A dictionary mapping old column names to new column names.

    Returns:
        DataFrame: A DataFrame with renamed columns.
    """
    return df.rename(columns=mapper)