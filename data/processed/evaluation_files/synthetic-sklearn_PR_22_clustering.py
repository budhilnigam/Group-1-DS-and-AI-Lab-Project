"""Clustering module for performing K-Means and DBSCAN clustering,
as well as silhouette analysis and the elbow method for optimal cluster
determination."""

from typing import Tuple, List
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.datasets import make_blobs


def kmeansCluster(data: np.ndarray, n_clusters: int, random_state: int = 42) -> Tuple[np.ndarray, KMeans]:
    """Perform K-Means clustering on the given data.

    Args:
        data (np.ndarray): The input data for clustering.
        n_clusters (int): The number of clusters to form.
        random_state (int, optional): Seed for random number generator. Default is 42.

    Returns:
        Tuple[np.ndarray, KMeans]: The cluster labels and the KMeans model.
    """
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state)
    labels = kmeans.fit_predict(data)
    return labels, kmeans


def dbscanCluster(data: np.ndarray, eps: float, min_samples: int) -> Tuple[np.ndarray, DBSCAN]:
    """Perform DBSCAN clustering on the given data.

    Args:
        data (np.ndarray): The input data for clustering.
        eps (float): The maximum distance between two samples for them to be considered
                     as in the same neighborhood.
        min_samples (int): The number of samples in a neighborhood for a point to be
                           considered as a core point.

    Returns:
        Tuple[np.ndarray, DBSCAN]: The cluster labels and the DBSCAN model.
    """
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    labels = dbscan.fit_predict(data)
    return labels, dbscan


def silhouetteAnalysis(data: np.ndarray, maxClusters: int) -> List[float]:
    """Perform silhouette analysis for a range of cluster counts.

    Args:
        data (np.ndarray): The input data for clustering.
        maxClusters (int): The maximum number of clusters to evaluate.

    Returns:
        List[float]: The silhouette scores for each number of clusters.
    """
    silhouetteScores = []
    for n_clusters in range(2, maxClusters + 1):
        labels, _ = kmeansCluster(data, n_clusters)
        if len(set(labels)) > 1:  # More than one cluster
            score = silhouette_score(data, labels)
            silhouetteScores.append(score)
        else:
            silhouetteScores.append(-1)  # Invalid score for single cluster
    return silhouetteScores


def elbowMethod(data: np.ndarray, maxClusters: int) -> None:
    """Plot the elbow method to determine the optimal number of clusters.

    Args:
        data (np.ndarray): The input data for clustering.
        maxClusters (int): The maximum number of clusters to evaluate.
    """
    inertia = []
    for n_clusters in range(1, maxClusters + 1):
        _, kmeans = kmeansCluster(data, n_clusters)
        inertia.append(kmeans.inertia_)

    plt.figure(figsize=(8, 5))
    plt.plot(range(1, maxClusters + 1), inertia, marker='o')
    plt.title('Elbow Method for Optimal k')
    plt.xlabel('Number of clusters')
    plt.ylabel('Inertia')
    plt.xticks(range(1, maxClusters + 1))
    plt.grid()
    plt.show()


if __name__ == "__main__":
    # Example usage
    sampleData, _ = make_blobs(n_samples=300, centers=4, cluster_std=0.60, random_state=0)
    elbowMethod(sampleData, maxClusters=10)
    silhouetteScores = silhouetteAnalysis(sampleData, maxClusters=10)
    print("Silhouette scores:", silhouetteScores)
    labels, _ = kmeansCluster(sampleData, n_clusters=4)
    print("K-Means cluster labels:", labels)