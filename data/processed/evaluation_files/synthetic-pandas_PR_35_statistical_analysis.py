"""
statistical_analysis.py

This module provides functions for performing statistical analysis on datasets using pandas and scipy.stats.
It includes functions for descriptive statistics, correlation analysis, and hypothesis testing.
"""

import os
import sys
import re
import pandas as pd
from scipy import stats
from typing import Tuple, Dict, Any


def descriptive_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate descriptive statistics for a given DataFrame.

    Parameters:
        df (pd.DataFrame): The DataFrame containing the data.

    Returns:
        Dict[str, Any]: A dictionary containing mean, median, mode, standard deviation, and variance.
    """
    stats_dict = {
        'mean': df.mean(),
        'median': df.median(),
        'mode': df.mode().iloc[0],
        'std_dev': df.std(),
        'variance': df.var()
    }
    return stats_dict


def correlation_analysis(df: pd.DataFrame, method: str = 'pearson'):
    """
    Calculate the correlation matrix for a given DataFrame.

    Parameters:
        df (pd.DataFrame): The DataFrame containing the data.
        method (str): The method to use for correlation ('pearson', 'kendall', 'spearman').

    Returns:
        pd.DataFrame: A DataFrame representing the correlation matrix.
    """
    if method not in ['pearson', 'kendall', 'spearman']:
        raise ValueError("Method must be one of 'pearson', 'kendall', or 'spearman'.")

    correlation_matrix = df.corr(method=method)
    return correlation_matrix


def hypothesis_test(sample1: pd.Series, sample2: pd.Series, test_type: str = 't-test'):
    if test_type == 't-test':
        stat, p_value = stats.ttest_ind(sample1, sample2, equal_var=False)
    elif test_type == 'mannwhitney':
        stat, p_value = stats.mannwhitneyu(sample1, sample2, alternative='two-sided')
    else:
        raise ValueError("Test type must be 't-test' or 'mannwhitney'.")

    return stat, p_value