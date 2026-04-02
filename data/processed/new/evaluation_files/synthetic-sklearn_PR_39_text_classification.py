"""
text_classification.py

This module implements text classification using TF-IDF vectorization and
Multinomial Naive Bayes classifier from scikit-learn. It includes functions
to vectorize text data and train a classifier on the provided dataset.
"""

import os
import sys
import re

from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


def vectorizeText(corpus: List[str]) -> Tuple[TfidfVectorizer, List[List[float]]]:
  """
  Vectorizes the input text corpus using TfidfVectorizer.

  Args:
      corpus (List[str]): A list of text documents to be vectorized.

  Returns:
      Tuple[TfidfVectorizer, List[List[float]]]: The fitted TfidfVectorizer
      and the transformed document-term matrix.
  """
  vectorizer = TfidfVectorizer()
  X = vectorizer.fit_transform(corpus)
  return vectorizer, X


def trainTextClassifier(X: List[List[float]], y: List[str]) -> MultinomialNB:
      """
      Trains a Multinomial Naive Bayes classifier on the provided data.

      Args:
          X (List[List[float]]): The document-term matrix.
          y (List[str]): The labels corresponding to the text documents.

      Returns:
          MultinomialNB: The trained Multinomial Naive Bayes classifier.
      """
      classifier = MultinomialNB()
      classifier.fit(X, y)
      return classifier


def evaluate_model(classifier: MultinomialNB, X_test: List[List[float]], y_test: List[str]) -> None:
      """
      Evaluates the trained classifier on the test data and prints the results.

      Args:
          classifier (MultinomialNB): The trained classifier.
          X_test (List[List[float]]): The test document-term matrix.
          y_test (List[str]): The true labels for the test data.
      """
      y_pred = classifier.predict(X_test)
      accuracy = accuracy_score(y_test, y_pred)
      report = classification_report(y_test, y_pred)

      print(f"Accuracy: {accuracy:.4f}")
      print("Classification Report:\n", report)


def main(corpus: List[str], labels: List[str]) -> None:
    """
    Main function to execute the text classification workflow.

    Args:
        corpus (List[str]): A list of text documents for classification.
        labels (List[str]): Corresponding labels for the documents.
    """
    X_train, X_test, y_train, y_test = train_test_split(corpus, labels, test_size=0.2, random_state=42)

    vectorizer, X_train_vec = vectorizeText(X_train)
    classifier = trainTextClassifier(X_train_vec, y_train)

    X_test_vec = vectorizer.transform(X_test)
    evaluate_model(classifier, X_test_vec, y_test)