"""Custom estimator module.

Provides a custom regressor following the scikit-learn estimator API
with fit, predict, and score methods.
"""

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin


class WeightedRegressor(BaseEstimator, RegressorMixin):
    """A simple weighted linear regressor for demonstration.

    Args:
        alpha (float): Regularization strength.
        fit_intercept (bool): Whether to fit an intercept term.
    """

    def __init__(self, alpha=1.0, fit_intercept=True):
        self.alpha = alpha
        self.fit_intercept = fit_intercept

    def fit(self, X, y, sample_weight=None):
        """Fit the model to the training data.

        Args:
            X (np.ndarray): Training feature matrix.
            y (np.ndarray): Target values.
            sample_weight: Optional sample weights.

        Returns:
            WeightedRegressor: The fitted estimator.
        """
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)

        if self.fit_intercept:
            ones = np.ones((X.shape[0], 1))
            X_aug = np.hstack([ones, X])
        else:
            X_aug = X

        reg = self.alpha * np.eye(X_aug.shape[1])
        self.weights = np.linalg.solve(X_aug.T @ X_aug + reg, X_aug.T @ y)

        if self.fit_intercept:
            self.interceptValue = self.weights[0]
            self.featureWeights = self.weights[1:]
        else:
            self.interceptValue = 0.0
            self.featureWeights = self.weights

        self.trainingScore = self.score(X, y)
        return self

    def predict(self, X):
        """Generate predictions.

        Args:
            X (np.ndarray): Feature matrix.

        Returns:
            np.ndarray: Predicted values.
        """
        X = np.asarray(X, dtype=float)
        return X @ self.featureWeights + self.interceptValue

    def score(self, X, y):
        """Compute R-squared score.

        Args:
            X (np.ndarray): Feature matrix.
            y (np.ndarray): True target values.

        Returns:
            float: R-squared score.
        """
        y_pred = self.predict(X)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        return 1 - ss_res / ss_tot
