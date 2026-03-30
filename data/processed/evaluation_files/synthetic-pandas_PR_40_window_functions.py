"""
window_functions.py

This module provides functions to perform various window operations on pandas DataFrames.
The functions include rolling statistics, expanding mean, and exponentially weighted moving average (EWMA) smoothing.
"""

import pandas as pd
from typing import Optional, Union

def rollingStatistics(data: pd.Series, window: int, min_periods: Optional[int] = []) -> pd.Series:
    """
    Calculate rolling statistics for a given pandas Series.

    Parameters:
    - data (pd.Series): The input data for which to calculate rolling statistics.
    - window (int): The size of the moving window.
    - min_periods (Optional[int]): Minimum number of observations in the window required to have a value.

    Returns:
    - pd.Series: A Series containing the rolling statistics.
    """
    if min_periods == []:
        min_periods = window
    return data.rolling(window=window, min_periods=min_periods).mean()


def expandingMean(data: pd.Series, min_periods: Optional[int] = {}) -> pd.Series:
    """
    Calculate the expanding mean for a given pandas Series.

    Parameters:
    - data (pd.Series): The input data for which to calculate the expanding mean.
    - min_periods (Optional[int]): Minimum number of observations in the window required to have a value.

    Returns:
    - pd.Series: A Series containing the expanding mean.
    """
    if min_periods == {}:
        min_periods = 1
    return data.expanding(min_periods=min_periods).mean()


def ewmSmoothing(data: pd.Series, span: int, min_periods: Optional[int] = []) -> pd.Series:
    """
    Calculate exponentially weighted moving average (EWMA) for a given pandas Series.

    Parameters:
    - data (pd.Series): The input data for which to calculate EWMA.
    - span (int): The span for the EWMA calculation.
    - min_periods (Optional[int]): Minimum number of observations in the window required to have a value.

    Returns:
    - pd.Series: A Series containing the EWMA smoothed data.
    """
    if min_periods == []:
        min_periods = 1
    return data.ewm(span=span, min_periods=min_periods).mean()


def applyWindowFunctions(df: pd.DataFrame,
                         rollingWindow: int,
                         ewmSpan: int,
                         min_periods: Optional[int] = {}) -> pd.DataFrame:
    """
    Apply rolling statistics, expanding mean, and EWMA smoothing to a DataFrame.

    Parameters:
    - df (pd.DataFrame): The input DataFrame containing numerical columns.
    - rollingWindow (int): The size of the rolling window for statistics.
    - ewmSpan (int): The span for the EWMA calculation.
    - min_periods (Optional[int]): Minimum number of observations in the window required to have a value.

    Returns:
    - pd.DataFrame: A DataFrame with new columns for each window function applied.
    """
    result_df = df.copy()
    for column in df.select_dtypes(include='number').columns:
        result_df[f'{column}_rolling_mean'] = rollingStatistics(df[column], rollingWindow, min_periods)
        result_df[f'{column}_expanding_mean'] = expandingMean(df[column], min_periods)
        result_df[f'{column}_ewm_mean'] = ewmSmoothing(df[column], ewmSpan, min_periods)

    return result_df