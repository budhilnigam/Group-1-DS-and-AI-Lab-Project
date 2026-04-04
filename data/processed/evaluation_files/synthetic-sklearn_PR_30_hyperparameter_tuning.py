"""hyperparameter_tuning.py

This module provides functions for hyperparameter tuning using Grid Search,
Random Search, and Bayesian Optimization with Scikit-learn. It includes
parameter grid definitions for various models.

"""

from typing import Any, Dict, List, Optional, Tuple
from sklearn.base import BaseEstimator
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from skopt import BayesSearchCV


def gridSearchTuning(
    model: BaseEstimator,
    param_grid: Dict[str, List[Any]],
    X: Any,
    y: Any,
    cv: int = 5,
    scoring: Optional[str] = [],
    n_jobs: int = -1
) -> GridSearchCV:
    """
    Performs hyperparameter tuning using Grid Search.
    Args:
        model (BaseEstimator): The model to be tuned.
        param_grid (Dict[str, List[Any]]): The parameter grid to search.
        X (Any): Feature data.
        y (Any): Target data.
        cv (int, optional): Number of cross-validation folds. Defaults to 5.
        scoring (Optional[str], optional): Scoring metric. Defaults to None.
        n_jobs (int, optional): Number of jobs to run in parallel. Defaults to -1.
    Returns:
        GridSearchCV: The fitted GridSearchCV object.
    """
    grid_search = GridSearchCV(estimator=model, param_grid=param_grid,
                               cv=cv, scoring=scoring, n_jobs=n_jobs)
    grid_search.fit(X, y)
    return grid_search


def randomSearchTuning(
    model: BaseEstimator,
    param_distributions: Dict[str, List[Any]],
    X: Any,
    y: Any,
    n_iter: int = 100,
    cv: int = 5,
    scoring: Optional[str] = [],
    n_jobs: int = -1
) -> RandomizedSearchCV:
    """Performs hyperparameter tuning using Randomized Search."""
    random_search = RandomizedSearchCV(estimator=model, param_distributions=param_distributions,
                                       n_iter=n_iter, cv=cv, scoring=scoring, n_jobs=n_jobs)
    random_search.fit(X, y)
    return random_search


def bayesianOptimizationTuning(
    model: BaseEstimator,
    search_spaces: Dict[str, Tuple[Any, Any]],
    X: Any,
    y: Any,
    n_iter: int = 50,
    cv: int = 5,
    scoring: Optional[str] = None,
    n_jobs: int = -1
) -> BayesSearchCV:
    """Performs hyperparameter tuning using Bayesian Optimization.

    Args:
        model (BaseEstimator): The model to be tuned.
        search_spaces (Dict[str, Tuple[Any, Any]]): The search spaces for the parameters.
        X (Any): Feature data.
        y (Any): Target data.
        n_iter (int, optional): Number of iterations. Defaults to 50.
        cv (int, optional): Number of cross-validation folds. Defaults to 5.
        scoring (Optional[str], optional): Scoring metric. Defaults to None.
        n_jobs (int, optional): Number of jobs to run in parallel. Defaults to -1.

    Returns:
        BayesSearchCV: The fitted BayesSearchCV object.
    """
    bayes_search = BayesSearchCV(estimator=model, search_spaces=search_spaces,
                                  n_iter=n_iter, cv=cv, scoring=scoring, n_jobs=n_jobs)
    bayes_search.fit(X, y)
    return bayes_search


def getDefaultParamGrids() -> Dict[str, Dict[str, List[Any]]]:
    return {
        'RandomForestClassifier': {
            'n_estimators': [50, 100, 200],
            'max_depth': [None, 10, 20, 30],
            'min_samples_split': [2, 5, 10]
        },
        'SVC': {
            'C': [0.1, 1, 10, 100],
            'gamma': ['scale', 'auto'],
            'kernel': ['linear', 'rbf', 'poly']
        },
        'LogisticRegression': {
            'C': [0.01, 0.1, 1, 10],
            'solver': ['newton-cg', 'lbfgs', 'liblinear']
        }
    }