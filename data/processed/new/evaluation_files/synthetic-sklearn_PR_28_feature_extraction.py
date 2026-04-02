"""Feature extraction module for text and image data using sklearn.

This module provides functions to extract features from text and image datasets
using Scikit-learn extractors. The text features are extracted using the TfidfVectorizer,
and image features are extracted using the Reshape function from sklearn's image module.
"""

import os
import sys
import re
from typing import List, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import FunctionTransformer
from sklearn.utils import check_array


def extract_text_features(documents: List[str] = []) -> np.ndarray:
    """Extract features from a list of text documents using TfidfVectorizer.

    Args:
        documents (List[str]): A list of text documents.

    Returns:
        np.ndarray: A 2D array of shape (n_samples, n_features) representing the
                    TF-IDF features of the input documents.
    """
    vectorizer = TfidfVectorizer()
    features = vectorizer.fit_transform(documents)
    return features.toarray()


def reshape_image(image: np.ndarray = np.array([])) -> np.ndarray:
    """Reshape image data to a flat array.

    Args:
        image (np.ndarray): The input image in the shape of (height, width, channels).

    Returns:
        np.ndarray: A flat array representing the reshaped image.
    """
    return image.flatten()


def extract_image_features(images: List[np.ndarray] = []) -> np.ndarray:
    """Extract features from a list of images by flattening them.

    Args:
        images (List[np.ndarray]): A list of images in the shape of (height, width, channels).

    Returns:
        np.ndarray: A 2D array of shape (n_samples, n_features) representing the
                    flattened features of the input images.
    """
    transformer = FunctionTransformer(func=reshape_image, validate=False)
    flattened_images = [transformer.transform(image.reshape(1, -1)) for image in images]
    return np.vstack(flattened_images)


def validate_inputs(documents: List[Any] = [], images: List[Any] = []) -> None:
    """Validate the input documents and images.

    Args:
        documents (List[Any]): The list of text documents to validate.
        images (List[Any]): The list of images to validate.

    Raises:
        ValueError: If the input documents or images are not valid.
    """
    if not documents or not isinstance(documents, list):
        raise ValueError("Documents must be a non-empty list.")

    if not images or not isinstance(images, list):
        raise ValueError("Images must be a non-empty list.")

    for img in images:
        if not isinstance(img, np.ndarray):
            raise ValueError("Each image must be a numpy ndarray.")

    check_array(documents, ensure_2d=False)  # Ensure documents are in a proper format
    check_array(images)  # Ensure images are in a proper format


def main(documents: List[str], images: List[np.ndarray]) -> None:
    """Main function to extract features from text and image data.

    Args:
        documents (List[str]): A list of text documents.
        images (List[np.ndarray]): A list of images.

    Returns:
        None
    """
    validate_inputs(documents, images)
    text_features = extract_text_features(documents)
    image_features = extract_image_features(images)

    print("Text Features Shape:", text_features.shape)
    print("Image Features Shape:", image_features.shape)