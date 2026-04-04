"""
time_series.py

Module for performing various time series operations using pandas.
Includes functionalities for resampling, calculating rolling means,
shifting data, and computing percentage changes with DatetimeIndex handling.
"""

import pandas as pd
from pandas import DataFrame, Series
import os
import sys
import re

def resample_time_series(data: DataFrame, freq: str, aggregation: str = 'mean') -> DataFrame:
    """
    Resample the time series data to a specified frequency.

    Args:
        data (DataFrame): Input time series data with a DatetimeIndex.
        freq (str): The frequency to resample the data (e.g., 'D', 'M', 'Y').
        aggregation (str): The aggregation function to apply (default is 'mean').

    Returns:
        DataFrame: Resampled time series data.
    """
    if aggregation not in ['mean', 'sum', 'min', 'max']:
        raise ValueError("Aggregation must be one of 'mean', 'sum', 'min', 'max'.")

    return data.resample(freq).agg(aggregation)

def rolling_mean(data: Series, window: int, min_periods: Optional[int] = None) -> Series:
    """
    Calculate the rolling mean of a time series.

    Args:
        data (Series): Input time series data.
        window (int): The number of observations used for the moving average.
        min_periods (Optional[int]): Minimum number of observations in the window required to have a value.

    Returns:
        Series: Rolling mean of the time series.
    """
    return data.rolling(window=window, min_periods=min_periods).mean()

def shift_time_series(data: Series, periods: int) -> Series:
    """
    Shift the time series data by a specified number of periods.

    Args:
        data (Series): Input time series data.
        periods (int): Number of periods to shift (positive for future, negative for past).

    Returns:
        Series: Shifted time series data.
    """
    return data.shift(periods)

def pct_change_time_series(data: Series, periods: int = 1) -> Series:
    """
    Calculate the percentage change between the current and a prior element.

    Args:
        data (Series): Input time series data.
        periods (int): Number of periods to shift for calculating percentage change.

    Returns:
        Series: Percentage change of the time series.
    """
    return data.pct_change(periods)

def main():
    # Example usage
    dates = pd.date_range(start='2023-01-01', periods=10, freq='D')
    values = pd.Series(range(10), index=dates)

    print("Original Data:")
    print(values)

    resampled_data = resample_time_series(values.to_frame(), '2D', 'sum')
    print("\nResampled Data (Sum every 2 days):")
    print(resampled_data)

    rolling_avg = rolling_mean(values, window=3)
    print("\nRolling Mean (Window = 3):")
    print(rolling_avg)

    shifted_data = shift_time_series(values, 2)
    print("\nShifted Data (2 periods forward):")
    print(shifted_data)

    pct_change_data = pct_change_time_series(values)
    print("\nPercentage Change:")
    print(pct_change_data)

if __name__ == "__main__":
    main()