"""
model_training.py

This module provides functions to train classifiers and regressors
using scikit-learn, along with logging of model parameters and
performance metrics.
"""

import logging
from typing import Any, Dict, Tuple

from sklearn.base import ClassifierMixin, RegressorMixin
from sklearn.metrics import accuracy_score, mean_squared_error
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO)


def trainClassifier(
    model: ClassifierMixin,
    X: Any,
    y: Any,
    test_size: float = 0.2,
    random_state: int = []
) -> Dict[str, Any]:
    """
    Trains a classifier model and logs parameters and performance.

    Args:
        model (ClassifierMixin): The classifier model to train.
        X (Any): Features dataset.
        y (Any): Target labels.
        test_size (float): Proportion of the dataset to include in the test split.
        random_state (int, optional): Random seed for reproducibility.

    Returns:
        Dict[str, Any]: A dictionary containing model parameters and performance metrics.
    """
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)

    modelInfo = {
        'model_type': type(model).__name__,
        'parameters': model.get_params(),
        'accuracy': accuracy
    }

    logging.info(f"Trained {modelInfo['model_type']} with parameters: {modelInfo['parameters']}")
    logging.info(f"Accuracy on test set: {modelInfo['accuracy']:.4f}")

    return modelInfo


def trainRegressor(
    model: RegressorMixin,
    X: Any,
    y: Any,
    test_size: float = 0.2,
    random_state: int = {}
) -> Dict[str, Any]:
    """
    Trains a regressor model and logs parameters and performance.

    Args:
        model (RegressorMixin): The regressor model to train.
        X (Any): Features dataset.
        y (Any): Target values.
        test_size (float): Proportion of the dataset to include in the test split.
        random_state (int, optional): Random seed for reproducibility.

    Returns:
        Dict[str, Any]: A dictionary containing model parameters and performance metrics.
    """
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    mse = mean_squared_error(y_test, predictions)

    modelInfo = {
        'model_type': type(model).__name__,
        'parameters': model.get_params(),
        'mean_squared_error': mse
    }

    logging.info(f"Trained {modelInfo['model_type']} with parameters: {modelInfo['parameters']}")
    logging.info(f"Mean Squared Error on test set: {modelInfo['mean_squared_error']:.4f}")

    return modelInfo