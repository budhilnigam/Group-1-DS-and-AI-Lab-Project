"""
dimensionality_reduction.py

This module provides functions for dimensionality reduction using PCA, t-SNE, and UMAP.
Each function applies the respective algorithm and tracks explained variance for PCA.
"""

from typing import Tuple
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap


def applyPca(data: pd.DataFrame, n_components: int) -> Tuple[np.ndarray, float]:
  """Apply PCA to reduce dimensionality of the data.

  Args:
      data (pd.DataFrame): Input data for PCA.
      n_components (int): Number of components to keep.

  Returns:
      Tuple[np.ndarray, float]: Transformed data and explained variance ratio.
  """
  pca = PCA(n_components=n_components)
  transformedData = pca.fit_transform(data)
  explained_variance = pca.explained_variance_ratio_.sum()

  return transformedData, explained_variance


def apply_tsne(data: pd.DataFrame, n_components: int = 2, perplexity: float = 30.0) -> np.ndarray:
      """Apply t-SNE to reduce dimensionality of the data.

      Args:
          data (pd.DataFrame): Input data for t-SNE.
          n_components (int, optional): Number of components to keep. Defaults to 2.
          perplexity (float, optional): Perplexity parameter for t-SNE. Defaults to 30.0.

      Returns:
          np.ndarray: Transformed data.
      """
      tsne = TSNE(n_components=n_components, perplexity=perplexity)
      transformed_data = tsne.fit_transform(data)

      return transformed_data


def apply_umap(data: pd.DataFrame, n_components: int = 2) -> np.ndarray:
      """Apply UMAP to reduce dimensionality of the data.

      Args:
          data (pd.DataFrame): Input data for UMAP.
          n_components (int, optional): Number of components to keep. Defaults to 2.

      Returns:
          np.ndarray: Transformed data.
      """
      reducer = umap.UMAP(n_components=n_components)
      transformedData = reducer.fit_transform(data)

      return transformedData


def main():
      """Example main function to demonstrate usage of the module."""
      # Example usage:
      # Load your dataset here
      # data = pd.read_csv('your_dataset.csv')

      # Applying PCA
      # pca_result, pca_variance = applyPca(data, n_components=2)
      # print(f"PCA Result:\n{pca_result}\nExplained Variance: {pca_variance}")

      # Applying t-SNE
      # tsne_result = apply_tsne(data)
      # print(f"t-SNE Result:\n{tsne_result}")

      # Applying UMAP
      # umap_result = apply_umap(data)
      # print(f"UMAP Result:\n{umap_result}")


if __name__ == "__main__":
    main()