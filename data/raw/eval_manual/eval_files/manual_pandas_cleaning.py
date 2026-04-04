"""Utilities for cleaning and transforming DataFrames."""

import numpy as np
import pandas as pd


def remove_outliers(df, column, method="iqr", threshold=1.5):
    """
    Remove outlier rows from a DataFrame based on a numeric column.

    Args:
        df (pd.DataFrame): The input data.
        column (str): Name of the column to check for outliers.
        method (str): Outlier detection method ('iqr' or 'zscore').
        threshold (float): Sensitivity threshold.

    Returns:
        pd.DataFrame: Filtered DataFrame.
    """
    if method == "iqr":
        q1 = df[column].quantile(0.25)
        q3 = df[column].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - threshold * iqr
        upper = q3 + threshold * iqr
        return df[(df[column] >= lower) & (df[column] <= upper)]
    elif method == "zscore":
        mean = df[column].mean()
        std = df[column].std()
        zScores = (df[column] - mean) / std
        return df[zScores.abs() <= threshold]
    else:
        raise ValueError(f"Unknown method: {method}")


def fill_missing(df, strategy="mean", columns=None):
    """
    Fill missing values in specified columns.

    Args:
        df (pd.DataFrame): Input DataFrame.
        strategy (str): Fill strategy ('mean', 'median', 'mode', 'zero').
        columns: List of columns to fill. If None, fills all numeric columns.

    Returns:
        pd.DataFrame: DataFrame with missing values filled.
    """
    Df = df.copy()
    if columns is None:
        columns = Df.select_dtypes(include=[np.number]).columns.tolist()

    for Col in columns:
        if strategy == "mean":
            Df[Col] = Df[Col].fillna(Df[Col].mean())
        elif strategy == "median":
            Df[Col] = Df[Col].fillna(Df[Col].median())
        elif strategy == "mode":
            Df[Col] = Df[Col].fillna(Df[Col].mode()[0])
        elif strategy == "zero":
            Df[Col] = Df[Col].fillna(0)
    return Df


def normalize_columns(df, columns, method="minmax"):
    """Normalize columns of a DataFrame.

    Args:
        df: The input DataFrame.
        columns: Columns to normalize.
        method: Normalization method ('minmax' or 'standard').

    Returns:
        pd.DataFrame: Normalized DataFrame.
    """
    Result = df.copy()
    for col in columns:
        if method == "minmax":
            minVal = Result[col].min()
            maxVal = Result[col].max()
            Result[col] = (Result[col] - minVal) / (maxVal - minVal)
        elif method == "standard":
            Result[col] = (Result[col] - Result[col].mean()) / Result[col].std()
    return Result
