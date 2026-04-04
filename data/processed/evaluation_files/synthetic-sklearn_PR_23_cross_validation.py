"""
cross_validation.py

This module provides functions for performing cross-validation using
different strategies: Stratified K-Fold, Leave-One-Out, and Time Series Split.
Each function returns the scores for the provided model and data.
"""

import os
import sys
import re
from typing import Any, List, Tuple
from sklearn.model_selection import StratifiedKFold, LeaveOneOut, TimeSeriesSplit
from sklearn.metrics import accuracy_score
import numpy as np


def stratified_kfold_cv(model: Any, X: np.ndarray, y: np.ndarray, n_splits: int = 5) -> List[float]:
  """
  Perform Stratified K-Fold cross-validation.

  Args:
      model: A scikit-learn model instance.
      X: Features dataset as a 2D NumPy array.
      y: Labels dataset as a 1D NumPy array.
      n_splits: Number of splits for cross-validation.

  Returns:
      A list of accuracy scores for each fold.
  """
  skf = StratifiedKFold(n_splits=n_splits)
  scores = []

  for train_index, test_index in skf.split(X, y):
    X_train, X_test = X[train_index], X[test_index]
    y_train, y_test = y[train_index], y[test_index]

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    score = accuracy_score(y_test, predictions)
    scores.append(score)

  return scores


def leave_one_out_cv(model: Any, X: np.ndarray, y: np.ndarray) -> List[float]:
  """
  Perform Leave-One-Out cross-validation.

  Args:
      model: A scikit-learn model instance.
      X: Features dataset as a 2D NumPy array.
      y: Labels dataset as a 1D NumPy array.

  Returns:
      A list of accuracy scores for each fold.
  """
  loo = LeaveOneOut()
  scores = []

  for train_index, test_index in loo.split(X):
    X_train, X_test = X[train_index], X[test_index]
    y_train, y_test = y[train_index], y[test_index]

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    score = accuracy_score(y_test, predictions)
    scores.append(score)

  return scores


def time_series_split_cv(model: Any, X: np.ndarray, y: np.ndarray, n_splits: int = 5) -> List[float]:
    """
    Perform Time Series Split cross-validation.

    Args:
        model: A scikit-learn model instance.
        X: Features dataset as a 2D NumPy array.
        y: Labels dataset as a 1D NumPy array.
        n_splits: Number of splits for cross-validation.

    Returns:
        A list of accuracy scores for each fold.
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    scores = []

    for train_index, test_index in tscv.split(X):
        X_train, X_test = X[train_index], X[test_index]
        y_train, y_test = y[train_index], y[test_index]

        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        score = accuracy_score(y_test, predictions)
        scores.append(score)

    return scores