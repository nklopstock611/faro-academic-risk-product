from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pickle
from sklearn.preprocessing import StandardScaler


BACKEND_DIR = Path(__file__).resolve().parents[1]

from helpers.data_loader import load_datasets
from helpers.preprocessing import prepare_dataset, FEATURE_COLS_V2
from helpers.knn_predictor import KNNPredictor


DEFAULT_THRESHOLD = 0.70
DEFAULT_TRAIN_CUTOFF = 202010
DEFAULT_VAL_CUTOFF = 202310
DEFAULT_FEATURE_ORDER = list(FEATURE_COLS_V2)
DEFAULT_MODEL_VERSION = "v2_knn_median_k20"


class V2PredictionService:
    """Loads and serves the current v2 production model artifact."""

    def __init__(
        self,
        data_dir: Path | None = None,
        artifact_path: Path | None = None,
        train_cutoff: int = DEFAULT_TRAIN_CUTOFF,
        val_cutoff: int = DEFAULT_VAL_CUTOFF,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        self.data_dir = Path(data_dir or BACKEND_DIR / "data")
        self.artifact_path = Path(artifact_path or BACKEND_DIR / "models" / "v2_model.pkl")
        self.train_cutoff = int(train_cutoff)
        self.val_cutoff = int(val_cutoff)
        self.threshold = float(threshold)
        self.feature_order = list(DEFAULT_FEATURE_ORDER)
        self.model_source = "artifact"
        self.model_version = DEFAULT_MODEL_VERSION

        self.scaler = None
        self.model = None

        if self.artifact_path.exists():
            self._load_artifact()
        else:
            self.model_source = "runtime_trained_fallback"
            self.scaler = StandardScaler()
            self.model = KNNPredictor(n_neighbors=20, aggregation="median")
            self._fit_fallback()

    def _load_artifact(self) -> None:
        with open(self.artifact_path, "rb") as f:
            artifact = pickle.load(f)

        self.model = artifact["model"]
        self.scaler = artifact.get("scaler")
        self.feature_order = list(artifact.get("feature_order", self.feature_order))
        self.threshold = float(artifact.get("threshold", self.threshold))
        self.model_version = str(artifact.get("model_version", self.model_version))

    def _fit_fallback(self) -> None:
        datasets = load_datasets(str(self.data_dir))
        df_train, df_val, _, _ = prepare_dataset(
            datasets,
            train_cutoff=self.train_cutoff,
            val_cutoff=self.val_cutoff,
            version="v2",
        )

        df_fit = pd.concat([df_train, df_val], ignore_index=True)
        df_fit = df_fit.dropna(subset=self.feature_order + ["PCT_CREDITOS_APROBADOS"]).copy()

        if df_fit.empty:
            raise ValueError("No training rows available for v2 model")

        X = df_fit[self.feature_order].values
        y = df_fit["PCT_CREDITOS_APROBADOS"].values

        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)

    def predict_from_feature_values(self, feature_values: dict[str, Any]) -> dict[str, Any]:
        ordered = [float(feature_values[col]) for col in self.feature_order]
        X = np.array([ordered], dtype=float)
        if self.scaler is not None:
            X = self.scaler.transform(X)

        if hasattr(self.model, "predict_with_uncertainty"):
            details = self.model.predict_with_uncertainty(X)[0]
            score = details["score"]
            p10 = details["p10"]
            p90 = details["p90"]
            std = details["std"]
            iqr = details["iqr"]
            neighbor_count = details["neighbor_count"]
            confidence_level = _confidence_from_iqr(iqr)
        else:
            score = float(self.model.predict(X)[0])
            p10 = p90 = std = iqr = None
            neighbor_count = None
            confidence_level = None

        return {
            "score": score,
            "at_risk": bool(score < self.threshold),
            "threshold": self.threshold,
            "feature_order": list(self.feature_order),
            "feature_vector": ordered,
            "model_source": self.model_source,
            "model_version": self.model_version,
            "score_p10": p10,
            "score_p90": p90,
            "score_std": std,
            "score_iqr": iqr,
            "confidence_level": confidence_level,
            "neighbor_count": neighbor_count,
        }


# IQR thresholds on PCT_CREDITOS_APROBADOS (range 0-1).
CONFIDENCE_IQR_HIGH = 0.10
CONFIDENCE_IQR_MEDIUM = 0.25


def _confidence_from_iqr(iqr: float | None) -> str | None:
    if iqr is None:
        return None
    if iqr <= CONFIDENCE_IQR_HIGH:
        return "alta"
    if iqr <= CONFIDENCE_IQR_MEDIUM:
        return "media"
    return "baja"


@lru_cache(maxsize=1)
def get_v2_prediction_service() -> V2PredictionService:
    return V2PredictionService()
