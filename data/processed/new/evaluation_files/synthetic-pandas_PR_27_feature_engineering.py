"""feature_engineering.py

This module provides functions for feature engineering in pandas DataFrames.
It includes capabilities for creating polynomial features, date-based features,
interaction terms, and binning continuous variables using pd.cut and pd.qcut.
"""

import pandas as pd
import numpy as np
from typing import List, Union, Tuple


def polynomial_features(df: pd.DataFrame, features: List[str], degree: int) -> pd.DataFrame:
    """Generate polynomial features for specified columns in a DataFrame.

    Args:
        df (pd.DataFrame): Input DataFrame.
        features (List[str]): List of column names to generate polynomial features for.
        degree (int): Degree of the polynomial features.

    Returns:
        pd.DataFrame: DataFrame with polynomial features added.
    """
    poly_df = df.copy()
    for feature in features:
        for d in range(2, degree + 1):
            poly_feature_name = f"{feature}_poly_{d}"
            poly_df[poly_feature_name] = poly_df[feature] ** d
    return poly_df


def date_features(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    """Extract date-based features from a date column in a DataFrame.

    Args:
        df (pd.DataFrame): Input DataFrame.
        date_column (str): Name of the date column.

    Returns:
        pd.DataFrame: DataFrame with extracted date features added.
    """
    df[date_column] = pd.to_datetime(df[date_column])
    df['year'] = df[date_column].dt.year
    df['month'] = df[date_column].dt.month
    df['day'] = df[date_column].dt.day
    df['day_of_week'] = df[date_column].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    return df


def interaction_terms(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    """Create interaction terms for specified columns in a DataFrame.

    Args:
        df (pd.DataFrame): Input DataFrame.
        features (List[str]): List of column names to create interaction terms for.

    Returns:
        pd.DataFrame: DataFrame with interaction terms added.
    """
    interaction_df = df.copy()
    for i in range(len(features)):
        for j in range(i + 1, len(features)):
            interaction_feature_name = f"{features[i]}_x_{features[j]}"
            interaction_df[interaction_feature_name] = (
                interaction_df[features[i]] * interaction_df[features[j]]
            )
    return interaction_df


def binning(df: pd.DataFrame, column: str, bins: Union[int, List[float]] = [], labels: Union[List[str], None] = []) -> pd.Series:
    """Bin a continuous variable into discrete intervals.

    Args:
        df (pd.DataFrame): Input DataFrame.
        column (str): Name of the column to bin.
        bins (Union[int, List[float]]): Number of bins or specific bin edges.
        labels (Union[List[str], None], optional): Labels for the bins. Defaults to [].

    Returns:
        pd.Series: Series of binned data.
    """
    if isinstance(bins, int):
        binned_data = pd.cut(df[column], bins=bins, labels=labels)
    else:
        binned_data = pd.cut(df[column], bins=bins, labels=labels, include_lowest=True)
    return binned_data


def quantile_binning(df: pd.DataFrame, column: str, quantiles: List[float], labels: List[str]) -> pd.Series:
    """Bin a continuous variable using quantiles.

    Args:
        df (pd.DataFrame): Input DataFrame.
        column (str): Name of the column to bin.
        quantiles (List[float]): List of quantiles to use for binning.
        labels (List[str]): Labels for the quantile bins.

    Returns:
        pd.Series: Series of quantile-binned data.
    """
    quantile_bins = [df[column].quantile(q) for q in quantiles]
    return binning(df, column, quantile_bins, labels)