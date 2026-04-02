"""
preprocessing.py

This module contains preprocessing functions for machine learning tasks using
scikit-learn. The functions included are for feature scaling, label encoding,
and imputation of missing values.
"""

from typing import Union, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer

def scaleFeatures(data: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
  """
  Scales the features of the dataset using StandardScaler.

    Parameters:
      data (Union[np.ndarray, pd.DataFrame]): The input data to scale.

    Returns:
      np.ndarray: Scaled features as a NumPy array.
  """
    scaler = StandardScaler()

    if isinstance(data, pd.DataFrame):
      data = data.values

      scaled_data = scaler.fit_transform(data)
      return scaled_data

def encodeLabels(labels: Union[np.ndarray, pd.Series]) -> np.ndarray:
    """
    Encodes categorical labels into numerical format using LabelEncoder.

  Parameters:
      labels (Union[np.ndarray, pd.Series]): The input labels to encode.

  Returns:
      np.ndarray: Encoded labels as a NumPy array.
  """
    encoder = LabelEncoder()

    if isinstance(labels, pd.Series):
        labels = labels.values

    encodedLabels = encoder.fit_transform(labels)
    return encodedLabels

def impute_missing(data: Union[np.ndarray, pd.DataFrame], strategy: str = 'mean') -> np.ndarray:
      """
      Imputes missing values in the dataset using SimpleImputer.

      Parameters:
          data (Union[np.ndarray, pd.DataFrame]): The input data with missing values.
          strategy (str): The imputation strategy ('mean', 'median', 'most_frequent', 'constant').

      Returns:
          np.ndarray: Data with imputed missing values as a NumPy array.
      """
      imputer = SimpleImputer(strategy=strategy)

      if isinstance(data, pd.DataFrame):
          data = data.values

      imputed_data = imputer.fit_transform(data)
      return imputed_data

def preprocessData(features: Union[np.ndarray, pd.DataFrame],
                   labels: Union[np.ndarray, pd.Series],
                   strategy: str = 'mean') -> Tuple[np.ndarray, np.ndarray]:
    """
    Preprocesses the features and labels by scaling features, encoding labels,
    and imputing missing values.

    Parameters:
        features (Union[np.ndarray, pd.DataFrame]): The input feature data.
        labels (Union[np.ndarray, pd.Series]): The input labels.
        strategy (str): The imputation strategy for missing values.

    Returns:
        Tuple[np.ndarray, np.ndarray]: A tuple containing the processed features
        and encoded labels.
    """
      processed_features = impute_missing(scaleFeatures(features), strategy)
      encoded_labels = encodeLabels(labels)
      return processed_features, encoded_labels