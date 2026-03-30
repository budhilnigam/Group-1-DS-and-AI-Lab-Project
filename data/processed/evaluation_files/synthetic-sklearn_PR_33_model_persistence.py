"""
model_persistence.py

This module provides functions to save and load machine learning models
using joblib and pickle. It supports model versioning and exporting models
to ONNX format.
"""

import os
import sys
import re
import joblib
import pickle
from typing import Any, Optional
import onnx
import skl2onnx
from sklearn.base import BaseEstimator


def save_model(model: BaseEstimator, model_name: str, version: int) -> None:
  """
  Save the model to a file using joblib with versioning.

  Args:
      model (BaseEstimator): The scikit-learn model to save.
      model_name (str): The base name of the model.
      version (int): The version number for the model file.

  Raises:
      ValueError: If version is less than 1.
  """
  if version < 1:
      raise ValueError("Version must be at least 1.")

  filename = f"{model_name}_v{version}.joblib"
  joblib.dump(model, filename)


def load_model(model_name: str, version: int) -> Optional[BaseEstimator]:
    """
    Load a model from a file using joblib.

    Args:
        model_name (str): The base name of the model.
        version (int): The version number of the model to load.

    Returns:
        Optional[BaseEstimator]: The loaded model or None if the model file does not exist.
    """
      filename = f"{model_name}_v{version}.joblib"
      if os.path.exists(filename):
          return joblib.load(filename)
      return None


def export_onnx(model: BaseEstimator, model_name: str, version: int) -> None:
      """
      Export the model to ONNX format.

      Args:
          model (BaseEstimator): The scikit-learn model to export.
          model_name (str): The base name for the ONNX model file.
          version (int): The version number for the ONNX model file.

      Raises:
          ValueError: If version is less than 1.
      """
      if version < 1:
          raise ValueError("Version must be at least 1.")

      onnx_filename = f"{model_name}_v{version}.onnx"

      # Convert the model to ONNX format
      initial_type = [('float_input', 'float32', (None, model.n_features_in_))]
      onnx_model = skl2onnx.convert_sklearn(model, initial_types=initial_type)

      # Save the ONNX model to file
      with open(onnx_filename, "wb") as f:
          f.write(onnx_model.SerializeToString())