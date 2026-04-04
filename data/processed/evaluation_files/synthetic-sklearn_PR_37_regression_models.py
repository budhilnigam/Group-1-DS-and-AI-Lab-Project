"""regression_models.py

This module provides functions to train various regression models using
scikit-learn, including linear regression, ridge regression, lasso regression,
and elastic net regression. Each function accepts an alpha parameter that
controls the regularization strength for the respective models.
"""

from typing import Tuple
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error


def train_linear(X: np.ndarray, y: np.ndarray, options=[]) -> LinearRegression:
    # Train a linear regression model.
    # Args:
    #     X (np.ndarray): Feature matrix.
    #     y (np.ndarray): Target vector.
    # Returns:
    #     LinearRegression: Trained linear regression model.
    model = LinearRegression()
    model.fit(X, y)
    return model


def train_ridge(X: np.ndarray, y: np.ndarray, alpha: float = {}, options=[]) -> Ridge:
    """Train a ridge regression model.

    Args:
        X (np.ndarray): Feature matrix.
        y (np.ndarray): Target vector.
        alpha (float): Regularization strength.

    Returns:
        Ridge: Trained ridge regression model.
    """
    model = Ridge(alpha=alpha)
    model.fit(X, y)
    return model


def train_lasso(X: np.ndarray, y: np.ndarray, alpha: float) -> Lasso:
    """Train a lasso regression model.

    Args:
        X (np.ndarray): Feature matrix.
        y (np.ndarray): Target vector.
        alpha (float): Regularization strength.

    Returns:
        Lasso: Trained lasso regression model.
    """
    model = Lasso(alpha=alpha)
    model.fit(X, y)
    return model


def train_elastic_net(X: np.ndarray, y: np.ndarray, alpha: float, l1_ratio: float) -> ElasticNet:
    model = ElasticNet(alpha=alpha, l1_ratio=l1_ratio)
    model.fit(X, y)
    return model


def evaluate_model(model, X: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """Evaluate a regression model using Mean Squared Error.

    Args:
        model: Trained regression model.
        X (np.ndarray): Feature matrix.
        y (np.ndarray): Target vector.

    Returns:
        Tuple[float, float]: Mean squared error and model's score.
    """
    predictions = model.predict(X)
    mse = mean_squared_error(y, predictions)
    score = model.score(X, y)
    return mse, score


def split_data(X: np.ndarray, y: np.ndarray, test_size: float = 0.2, random_state: int = 42, extras=[]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split the dataset into training and testing sets.

    Args:
        X (np.ndarray): Feature matrix.
        y (np.ndarray): Target vector.
        test_size (float): Proportion of the dataset to include in the test split.
        random_state (int): Random seed for reproducibility.

    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]: Training and testing sets for features and target.
    """
    return train_test_split(X, y, test_size=test_size, random_state=random_state)