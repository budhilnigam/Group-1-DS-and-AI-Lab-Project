"""feature_selection.py

This module provides functions for feature selection using various techniques
from the scikit-learn library. The techniques implemented include SelectKBest,
Recursive Feature Elimination, and Variance Thresholding. Each function allows for
customization through parameters to suit different datasets and requirements.

Author: Your Name
"""

from typing import Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, RFE, VarianceThreshold
from sklearn.base import BaseEstimator
from sklearn.model_selection import train_test_split
import os
import sys
import re

def selectKBestFeatures(X: pd.DataFrame, y: pd.Series, k: int) -> Tuple[pd.DataFrame, np.ndarray]:
  """Select the top k features based on univariate statistical tests.

  Args:
      X (pd.DataFrame): Feature set.
      y (pd.Series): Target variable.
      k (int): Number of top features to select.

  Returns:
      Tuple[pd.DataFrame, np.ndarray]: DataFrame of selected features and
                                         array of feature scores.
  """
  selector = SelectKBest(k=k)
  X_new = selector.fit_transform(X, y)
  feature_scores = selector.scores_
  selected_features = X.columns[selector.get_support()]

  return pd.DataFrame(X_new, columns=selected_features), feature_scores

def recursiveFeatureElimination(X: pd.DataFrame, y: pd.Series, estimator: BaseEstimator, n_features_to_select: Optional[int] = None) -> pd.DataFrame:
      """Select features using recursive feature elimination with cross-validation.

      Args:
          X (pd.DataFrame): Feature set.
          y (pd.Series): Target variable.
          estimator (BaseEstimator): A supervised learning estimator.
          n_features_to_select (Optional[int]): Number of features to select.
                                                 If None, half of the features will be selected.

      Returns:
          pd.DataFrame: DataFrame of selected features.
      """
      rfe = RFE(estimator, n_features_to_select=n_features_to_select)
      X_new = rfe.fit_transform(X, y)
      selected_features = X.columns[rfe.support_]

      return pd.DataFrame(X_new, columns=selected_features)

def variance_threshold_selection(X: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Remove features with variance below a specified threshold.

    Args:
        X (pd.DataFrame): Feature set.
        threshold (float): Variance threshold for feature selection.

    Returns:
        pd.DataFrame: DataFrame of features with variance above the threshold.
    """
    variance_filter = VarianceThreshold(threshold=threshold)
    X_new = variance_filter.fit_transform(X)
    selected_features = X.columns[variance_filter.get_support()]

    return pd.DataFrame(X_new, columns=selected_features)

def main() -> None:
    """Main function to demonstrate feature selection methods."""
    # Sample data for demonstration (to be replaced with actual data)
    from sklearn.datasets import load_iris
    iris = load_iris()
    X, y = pd.DataFrame(iris.data, columns=iris.feature_names), pd.Series(iris.target)

    # Feature selection examples
    print("Select K Best Features:")
    X_k_best, scores = selectKBestFeatures(X, y, k=2)
    print(X_k_best)
    print("Feature Scores:", scores)

    print("\nRecursive Feature Elimination:")
    estimator = RFE(estimator=VarianceThreshold(), n_features_to_select=2)
    X_rfe = recursiveFeatureElimination(X, y, estimator)
    print(X_rfe)

    print("\nVariance Threshold Selection:")
    X_var = variance_threshold_selection(X, threshold=0.5)
    print(X_var)

if __name__ == "__main__":
    main()