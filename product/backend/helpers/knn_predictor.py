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

    def _aggregate(self, neighbor_y: np.ndarray, dists: np.ndarray) -> float:
        if self.aggregation == 'median':
            return float(np.median(neighbor_y))
        if self.aggregation == 'distance':
            w = 1.0 / (dists + 1e-10)
            w /= w.sum()
            return float(np.dot(w, neighbor_y))
        return float(np.mean(neighbor_y))

    def predict(self, X_scaled: np.ndarray) -> np.ndarray:
        distances, indices = self._nn.kneighbors(X_scaled)
        preds = [self._aggregate(self._y_train[idx], dists)
                 for dists, idx in zip(distances, indices)]
        return np.clip(np.array(preds), 0.0, 1.0)

    def predict_with_uncertainty(self, X_scaled: np.ndarray) -> list[dict]:
        """Predict and expose neighbor-based uncertainty stats per row.

        Returns a list of dicts with: score, p10, p90, std, iqr,
        neighbor_count, mean_distance.
        """
        distances, indices = self._nn.kneighbors(X_scaled)
        results = []
        for dists, idx in zip(distances, indices):
            neighbor_y = self._y_train[idx]
            score = float(np.clip(self._aggregate(neighbor_y, dists), 0.0, 1.0))
            results.append({
                'score': score,
                'p10': float(np.clip(np.percentile(neighbor_y, 10), 0.0, 1.0)),
                'p90': float(np.clip(np.percentile(neighbor_y, 90), 0.0, 1.0)),
                'std': float(np.std(neighbor_y, ddof=1)) if len(neighbor_y) > 1 else 0.0,
                'iqr': float(np.percentile(neighbor_y, 75) - np.percentile(neighbor_y, 25)),
                'neighbor_count': int(len(neighbor_y)),
                'mean_distance': float(np.mean(dists)),
            })
        return results
