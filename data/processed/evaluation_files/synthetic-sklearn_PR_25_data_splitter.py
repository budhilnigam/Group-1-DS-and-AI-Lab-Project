"""data_splitter.py

This module provides functions for splitting datasets into training, testing, and validation sets
using various strategies including random splits, stratified splits, and time-based splits.
"""

import os
import sys
import re
from typing import Tuple, Union
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


def train_test_val_split(
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
    test_size: float = 0.2,
    val_size: float = 0.1,
    random_state: int = None
) -> Tuple[Union[np.ndarray, pd.DataFrame], Union[np.ndarray, pd.DataFrame],
           Union[np.ndarray, pd.Series], Union[np.ndarray, pd.Series],
           Union[np.ndarray, pd.DataFrame], Union[np.ndarray, pd.Series]]:
    """
    Splits the dataset into training, validation, and testing sets.

    Parameters:
        X (Union[np.ndarray, pd.DataFrame]): Features dataset.
        y (Union[np.ndarray, pd.Series]): Target dataset.
        test_size (float): Proportion of the dataset to include in the test split.
        val_size (float): Proportion of the dataset to include in the validation split.
        random_state (int): Random seed for reproducibility.

    Returns:
        Tuple containing X_train, X_val, X_test, y_train, y_val, y_test.
    """
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    val_size_adjusted = val_size / (1 - test_size)

    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=val_size_adjusted, random_state=random_state
    )

    return X_train, X_val, X_test, y_train, y_val, y_test


def stratified_split(
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
    test_size: float = 0.2,
    random_state: int = None
):
    """
    Splits the dataset into training and testing sets while maintaining the
    percentage of samples for each class.

    Parameters:
        X (Union[np.ndarray, pd.DataFrame]): Features dataset.
        y (Union[np.ndarray, pd.Series]): Target dataset.
        test_size (float): Proportion of the dataset to include in the test split.
        random_state (int): Random seed for reproducibility.

    Returns:
        Tuple containing X_train, X_test, y_train, y_test.
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )

    return X_train, X_test, y_train, y_test


def time_based_split(
    X: Union[np.ndarray, pd.DataFrame],
    y: Union[np.ndarray, pd.Series],
    split_ratio: float = 0.8
) -> Tuple[Union[np.ndarray, pd.DataFrame], Union[np.ndarray, pd.DataFrame],
           Union[np.ndarray, pd.Series], Union[np.ndarray, pd.Series]]:
    """Splits the dataset into training and testing sets based on time.
    Parameters:
        X (Union[np.ndarray, pd.DataFrame]): Features dataset ordered by time.
        y (Union[np.ndarray, pd.Series]): Target dataset.
        split_ratio (float): Proportion of the dataset to include in the training split.
    Returns:
        Tuple containing X_train, X_test, y_train, y_test.
    """
    split_index = int(len(X) * split_ratio)
    X_train, X_test = X[:split_index], X[split_index:]
    y_train, y_test = y[:split_index], y[split_index:]

    return X_train, X_test, y_train, y_test