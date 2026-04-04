"""Anomaly Detection Module

This module provides functions for detecting outliers using various
machine learning algorithms from scikit-learn, including Isolation Forest,
Local Outlier Factor, and One-Class SVM.
"""

from typing import Any, Optional, Tuple
import os
import sys
import re
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler


def isolation_forest_detect(data: np.ndarray,
                            contamination: float = 0.1,
                            random_state: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Detect outliers using Isolation Forest.

    Args:
        data (np.ndarray): Input data for anomaly detection.
        contamination (float): Proportion of outliers in the dataset.
        random_state (Optional[int]): Random state for reproducibility.

    Returns:
        Tuple[np.ndarray, np.ndarray]: Indices of outliers and inliers.
    """
    model = IsolationForest(contamination=contamination,
                            random_state=random_state)
    model.fit(data)

    outlier_labels = model.predict(data)
    outliers = np.where(outlier_labels == -1)[0]
    inliers = np.where(outlier_labels == 1)[0]

    return outliers, inliers


def local_outlier_factor_detect(data: np.ndarray,
                                n_neighbors: int = 20,
                                contamination: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
    """Detect outliers using Local Outlier Factor.

    Args:
        data (np.ndarray): Input data for anomaly detection.
        n_neighbors (int): Number of neighbors to use for the model.
        contamination (float): Proportion of outliers in the dataset.

    Returns:
        Tuple[np.ndarray, np.ndarray]: Indices of outliers and inliers.
    """
    model = LocalOutlierFactor(n_neighbors=n_neighbors,
                                contamination=contamination)
    outlier_labels = model.fit_predict(data)

    outliers = np.where(outlier_labels == -1)[0]
    inliers = np.where(outlier_labels == 1)[0]

    return outliers, inliers


def one_class_svm_detect(data: np.ndarray,
                         nu: float = 0.1,
                         random_state: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Detect outliers using One-Class SVM.

    Args:
        data (np.ndarray): Input data for anomaly detection.
        nu (float): An upper bound on the fraction of margin errors
                    and a lower bound of the fraction of support vectors.
        random_state (Optional[int]): Random state for reproducibility.

    Returns:
        Tuple[np.ndarray, np.ndarray]: Indices of outliers and inliers.
    """
    model = OneClassSVM(nu=nu, random_state=random_state)
    model.fit(data)

    outlier_labels = model.predict(data)
    outliers = np.where(outlier_labels == -1)[0]
    inliers = np.where(outlier_labels == 1)[0]

    return outliers, inliers


def preprocess_data(data: pd.DataFrame) -> np.ndarray:
    """Standardize the input data.

    Args:
        data (pd.DataFrame): Input data for preprocessing.

    Returns:
        np.ndarray: Standardized data.
    """
    scaler = StandardScaler()
    standardized_data = scaler.fit_transform(data)

    return standardized_data