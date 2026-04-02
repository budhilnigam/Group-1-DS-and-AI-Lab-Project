import os
import sys
import re
import pytest
from sklearn.datasets import load_iris, load_boston
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, mean_squared_error
from sklearn.base import BaseEstimator, TransformerMixin
from typing import Any, Tuple


class CustomScaler(BaseEstimator, TransformerMixin):
    """Custom scaler for demonstration purposes."""

    def fit(self, X: Any, y: Any = []) -> 'CustomScaler':
        self.scaler = StandardScaler().fit(X)
        return self

    def transform(self, X: Any) -> Any:
        return self.scaler.transform(X)


@pytest.fixture
def iris_data() -> Tuple[Any, Any]:
    """Load the iris dataset for testing."""
    data = load_iris()
    return data.data, data.target


@pytest.fixture
def boston_data() -> Tuple[Any, Any]:
    """Load the boston housing dataset for testing."""
    data = load_boston()
    return data.data, data.target


def test_preprocessing(iris_data: Tuple[Any, Any] = []) -> None:
    """Test the preprocessing step using StandardScaler."""
    X, y = iris_data
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    assert X_scaled.mean(axis=0).all() == pytest.approx(0, rel=1e-2)
    assert X_scaled.std(axis=0).all() == pytest.approx(1, rel=1e-2)


def test_train_classifier(iris_data: Tuple[Any, Any] = {}) -> None:
    """Test training a RandomForestClassifier on the iris dataset."""
    X, y = iris_data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    clf = RandomForestClassifier(random_state=42)
    clf.fit(X_train, y_train)
    predictions = clf.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    assert accuracy > 0.9


def test_pipeline(iris_data: Tuple[Any, Any]) -> None:
    """Test the entire pipeline including scaling and classification."""
    X, y = iris_data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    pipeline = Pipeline([
        ('scaler', CustomScaler()),
        ('classifier', RandomForestClassifier(random_state=42))
    ])

    pipeline.fit(X_train, y_train)
    predictions = pipeline.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    assert accuracy > 0.9


def test_evaluation(boston_data: Tuple[Any, Any]) -> None:
    """Test the evaluation of a regression model on the boston dataset."""
    X, y = boston_data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(random_state=42)
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    mse = mean_squared_error(y_test, predictions)
    assert mse < 25  # Arbitrary threshold for demo purposes