"""Abstract base class for all predictors (clustering-based and supervised)."""
from abc import ABC, abstractmethod
import numpy as np


class BasePredictor(ABC):
    """Common interface for everything that lives inside a hierarchical level group.

    A predictor is trained on (X_scaled, y) for one group at one level and
    predicts PCT_CREDITOS_APROBADOS ∈ [0, 1] for new enrollments.

    Both clustering-based models (K-Means, GMM, FCM) and supervised models
    (Ridge, KNN, SVR) implement this interface — the hierarchical framework
    does not need to know which kind it is using.
    """

    @abstractmethod
    def fit(self, X_scaled: np.ndarray, y: np.ndarray) -> 'BasePredictor':
        """Fit on scaled features X and credit-approval rates y ∈ [0, 1]."""

    @abstractmethod
    def predict(self, X_scaled: np.ndarray) -> np.ndarray:
        """Return predicted PCT_CREDITOS_APROBADOS for each row. Clipped to [0, 1]."""
