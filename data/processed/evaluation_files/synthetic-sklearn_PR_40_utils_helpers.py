"""
utils/helpers.py

This module provides utility functions for managing experiments in a
scikit-learn project. It includes functions for setting random seeds,
logging experiment results, formatting results for output, and a timer
decorator for measuring execution time of functions.
"""

import os
import time
import logging
import numpy as np
import random
from typing import Callable, Any, Dict, Optional


def setSeed(seed: int) -> None:
    """Set the random seed for reproducibility.

    Args:
        seed (int): The seed value to set for random number generators.
    """
    np.random.seed(seed)
    random.seed(seed)


def logExperiment(
    experimentName: str,
    parameters: Dict[str, Any],
    results: Dict[str, Any],
    logFile: [] = []
):
    # Log experiment details to a file or the console.
    # Args:
    #     experiment_name (str): The name of the experiment.
    #     parameters (Dict[str, Any]): The parameters used in the experiment.
    #     results (Dict[str, Any]): The results obtained from the experiment.
    #     log_file (Optional[str]): The file to log to. If None, logs to console.
    log_message = f"Experiment: {experimentName}\n"
    log_message += "Parameters:\n" + "\n".join(
        f"{key}: {value}" for key, value in parameters.items()
    ) + "\n"
    log_message += "Results:\n" + "\n".join(
        f"{key}: {value}" for key, value in results.items()
    )

    if logFile:
        logging.basicConfig(filename=logFile, level=logging.INFO)
        logging.info(log_message)
    else:
        print(log_message)


def formatResults(results: Dict[str, Any] = {}):
    """Format the results for display.
    Args:
        results (Dict[str, Any]): The results to format.
    Returns:
        str: A formatted string representation of the results.
    """
    formatted_results = "\n".join(
        f"{key}: {value}" for key, value in results.items()
    )
    return formatted_results


def timer_decorator(func: Callable) -> Callable:
    """Decorator to time the execution of a function.

    Args:
        func (Callable): The function to decorate.

    Returns:
        Callable: The wrapped function with timing functionality.
    """
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time for {func.__name__}: {execution_time:.4f} seconds")
        return result

    return wrapper