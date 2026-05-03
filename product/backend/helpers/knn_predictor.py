"""K-Nearest Neighbors predictor with configurable aggregation.

Supports three aggregation modes:
  mean    – arithmetic mean of neighbor targets (equivalent to sklearn default)
  median  – median of neighbor targets (more robust to outliers)
  distance – inverse-distance weighted mean
"""
import numpy as np
from sklearn.neighbors import NearestNeighbors
from .base_predictor import BasePredictor


class KNNPredictor(BasePredictor):

    def __init__(self, n_neighbors=5, aggregation='mean', random_state=42):
        """
        Parameters
        ----------
        n_neighbors  : int   – number of neighbors
        aggregation  : str   – 'mean' | 'median' | 'distance'
        """
        if aggregation not in ('mean', 'median', 'distance'):
            raise ValueError("aggregation must be 'mean', 'median', or 'distance'")
        self.n_neighbors = n_neighbors
        self.aggregation = aggregation
        self._nn = None
        self._y_train = None

    def fit(self, X_scaled: np.ndarray, y: np.ndarray) -> 'KNNPredictor':
        k = min(self.n_neighbors, len(X_scaled))
        self._nn = NearestNeighbors(n_neighbors=k).fit(X_scaled)
        self._y_train = y.copy()
        self._k = k
        return self

    def predict(self, X_scaled: np.ndarray) -> np.ndarray:
        distances, indices = self._nn.kneighbors(X_scaled)
        preds = []
        for dists, idx in zip(distances, indices):
            neighbor_y = self._y_train[idx]
            if self.aggregation == 'median':
                pred = float(np.median(neighbor_y))
            elif self.aggregation == 'distance':
                w = 1.0 / (dists + 1e-10)
                w /= w.sum()
                pred = float(np.dot(w, neighbor_y))
            else:  # mean
                pred = float(np.mean(neighbor_y))
            preds.append(pred)
        return np.clip(np.array(preds), 0.0, 1.0)
