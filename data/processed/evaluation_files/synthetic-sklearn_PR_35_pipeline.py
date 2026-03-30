import os
import sys
import re
"""pipeline.py

Module to construct sklearn pipelines for preprocessing and modeling.
This module provides functions to build preprocessing pipelines and full
pipelines that include both preprocessing and model training steps.
"""

from typing import List, Tuple, Any
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.base import BaseEstimator, TransformerMixin


class CustomTransformer(BaseEstimator, TransformerMixin):
    """Custom transformer example for demonstration purposes.
    """

    def fit(self, X: Any, y: Any = None) -> 'CustomTransformer':
        return self

    def transform(self, X: Any) -> Any:
        return X  # Replace with actual transformation logic


def build_preprocessing_pipeline(numeric_features: List[str],
                                 categorical_features: List[str]) -> Pipeline:
    """Build a preprocessing pipeline with numeric and categorical processing.

    Args:
        numeric_features (List[str]): List of numeric feature names.
        categorical_features (List[str]): List of categorical feature names.

    Returns:
        Pipeline: A scikit-learn pipeline for preprocessing.
    """
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ]
    )

    return preprocessor


def build_full_pipeline(numeric_features: List[str],
                        categorical_features: List[str],
                        model: Any) -> Pipeline:
    """Build a full pipeline including preprocessing and model.

    Args:
        numeric_features (List[str]): List of numeric feature names.
        categorical_features (List[str]): List of categorical feature names.
        model (Any): A scikit-learn estimator (model) to include in the pipeline.

    Returns:
        Pipeline: A scikit-learn pipeline for preprocessing and model training.
    """
    preprocessor = build_preprocessing_pipeline(numeric_features, categorical_features)

    full_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('model', model)
    ])

    return full_pipeline


def fit_pipeline(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series) -> Pipeline:
    """Fit the pipeline to the training data.

    Args:
        pipeline (Pipeline): The pipeline to fit.
        X (pd.DataFrame): Training data.
        y (pd.Series): Target labels.

    Returns:
        Pipeline: The fitted pipeline.
    """
    pipeline.fit(X, y)
    return pipeline


def predict_with_pipeline(pipeline: Pipeline, X: pd.DataFrame) -> Any:
    """Make predictions using the fitted pipeline.

    Args:
        pipeline (Pipeline): The fitted pipeline.
        X (pd.DataFrame): New data for predictions.

    Returns:
        Any: Predicted values.
    """
    return pipeline.predict(X)