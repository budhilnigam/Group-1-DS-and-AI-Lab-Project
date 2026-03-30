"""
model_evaluation.py

This module provides functions to evaluate classifiers and regressors using
common performance metrics such as accuracy, precision, recall, and mean
absolute error (MAE). The functions return a dictionary containing the
calculated metrics for easy access.
"""

from typing import Dict, Any
from sklearn.metrics import accuracy_score, precision_score, recall_score, mean_absolute_error
from sklearn.base import ClassifierMixin, RegressorMixin


def evaluateClassifier(y_true: Any, y_pred: Any) -> Dict[str, float]:
    """
    Evaluate the performance of a classifier.

    Parameters:
    y_true (Any): True labels of the data.
    y_pred (Any): Predicted labels from the classifier.

    Returns:
    Dict[str, float]: A dictionary containing accuracy, precision, and recall.
    """
    metrics = {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, average='weighted'),
        'recall': recall_score(y_true, y_pred, average='weighted')
    }
    return metrics


def evaluateRegressor(y_true: Any, y_pred: Any) -> Dict[str, float]:
    """
    Evaluate the performance of a regressor.

    Parameters:
    y_true (Any): True values of the data.
    y_pred (Any): Predicted values from the regressor.

    Returns:
    Dict[str, float]: A dictionary containing mean absolute error (MAE).
    """
    metrics = {
        'mae': mean_absolute_error(y_true, y_pred)
    }
    return metrics


def evaluateModel(model: Any, X_test: Any, y_test: Any) -> Dict[str, Any]:
    """
    Evaluate the given model, which can be a classifier or regressor.

    Parameters:
    model (Any): The model to evaluate (should be either a classifier or regressor).
    X_test (Any): Test features.
    y_test (Any): True labels or values for the test set.

    Returns:
    Dict[str, Any]: A dictionary containing the evaluation metrics.
    """
    y_pred = model.predict(X_test)

    if isinstance(model, ClassifierMixin):
        return evaluateClassifier(y_test, y_pred)
    elif isinstance(model, RegressorMixin):
        return evaluateRegressor(y_test, y_pred)
    else:
        raise ValueError("Model must be either a classifier or a regressor")