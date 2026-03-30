"""
metrics_utils.py

Utility functions for evaluating machine learning models using scikit-learn.
Includes functions for generating classification reports, plotting confusion matrices,
and plotting ROC curves.
"""

import os
import sys
import re
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc
import seaborn as sns
from typing import Dict, Any, Tuple


def classification_report_dict(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """
    Generate a classification report as a dictionary.

    Parameters:
    y_true (np.ndarray): True labels.
    y_pred (np.ndarray): Predicted labels.

    Returns:
    Dict[str, Any]: Classification report as a dictionary.
    """
    report = classification_report(y_true, y_pred, output_dict=True)
    return report


def plot_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray,
                          labels: list = None, title: str = 'Confusion Matrix') -> None:
    """
    Plot the confusion matrix using seaborn heatmap.

    Parameters:
    y_true (np.ndarray): True labels.
    y_pred (np.ndarray): Predicted labels.
    labels (list, optional): List of label names. Defaults to None.
    title (str, optional): Title of the plot. Defaults to 'Confusion Matrix'.
    """
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                 xticklabels=labels, yticklabels=labels)
    plt.title(title)
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    plt.show()


def plot_roc_curve(y_true: np.ndarray, y_scores: np.ndarray,
                   title: str = 'Receiver Operating Characteristic') -> None:
    """
    Plot the Receiver Operating Characteristic (ROC) curve.

    Parameters:
    y_true (np.ndarray): True binary labels.
    y_scores (np.ndarray): Target scores, probability estimates of the positive class.
    title (str, optional): Title of the plot. Defaults to 'Receiver Operating Characteristic'.
    """
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)

    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='blue', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='red', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title(title)
    plt.legend(loc='lower right')
    plt.show()