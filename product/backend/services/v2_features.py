from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR / "models") not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR / "models"))

from consultar_estudiante import consultar_estudiante
from helpers.data_loader import load_datasets
from helpers.preprocessing import FEATURE_COLS_BASE, FEATURE_COLS_V2
from helpers.difficulty_features import _compute_rate_tables, DEFAULT_THRESHOLDS


BASE_FEATURE_NAME_MAP = {
    "pga_anterior": "PGA_ANTERIOR",
    "semestres_anteriores": "SEMESTRES_ANTERIORES",
    "pct_creditos_anterior": "PCT_CREDITOS_ANTERIOR",
}

DEFAULT_BASE_FEATURES = [
    "PGA_ANTERIOR",
    "SEMESTRES_ANTERIORES",
    "PCT_CREDITOS_ANTERIOR",
    "NUM_CURSOS",
    "CREDITOS_TOTALES",
]

DEFAULT_V2_FEATURES = DEFAULT_BASE_FEATURES + [
    "DIFF_MEAN_WEIGHTED",
    "DIFF_MIN",
    "DIFF_STD",
]


@dataclass
class CourseDifficulty:
    course_code: str
    credits: float
    difficulty_rate: float
    source_level: str
    professor: str | None = None


class V2FeatureService:
    """Builds v2 model features from raw backend inputs."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir or BACKEND_DIR / "data")
        self.datasets = load_datasets(str(self.data_dir))
        self.thresholds = dict(DEFAULT_THRESHOLDS)

        self.df_materias = self._get_dataset("materias", "historial_materias", "materias_estudiante")
        self.df_cursos_profesores = self._get_dataset(
            "cursos_profesores",
            "curso_profesores",
            "historial_cursos_profesores",
        )
        self.df_oferta = self._get_dataset("oferta", "oferta_academica")

        self.df_materias = self.df_materias.copy()
        self.df_cursos_profesores = self.df_cursos_profesores.copy()
        self.df_oferta = self.df_oferta.copy()

        self.df_materias["PERIODO"] = self.df_materias["PERIODO"].astype(int)
        self.df_cursos_profesores["PERIODO"] = self.df_cursos_profesores["PERIODO"].astype(int)

        self.course_to_credits = self._build_course_to_credits()
        self.course_to_department = self._build_course_to_department()
        self.crn_to_professor = self._build_crn_to_professor()
        self.latest_period = int(self.df_materias["PERIODO"].max())

        self.base_feature_cols = list(globals().get("FEATURE_COLS_BASE", DEFAULT_BASE_FEATURES))
        self.v2_feature_cols = list(globals().get("FEATURE_COLS_V2", DEFAULT_V2_FEATURES))

    def _get_dataset(self, *keys: str) -> pd.DataFrame:
        for key in keys:
            if key in self.datasets:
                return self.datasets[key]
        known_keys = ", ".join(sorted(self.datasets.keys()))
        raise KeyError(f"Dataset not found. Tried {keys}. Available: {known_keys}")

    def _build_course_to_credits(self) -> dict[str, float]:
        if "NUMERO_CREDITOS" in self.df_materias.columns:
            credits_df = (
                self.df_materias[["CODIGO_CURSO", "NUMERO_CREDITOS"]]
                .dropna(subset=["CODIGO_CURSO", "NUMERO_CREDITOS"])
                .drop_duplicates(subset=["CODIGO_CURSO"], keep="first")
            )
        else:
            credits_df = (
                self.df_oferta[["CODIGO_CURSO", "NUMERO_CREDITOS"]]
                .dropna(subset=["CODIGO_CURSO", "NUMERO_CREDITOS"])
                .drop_duplicates(subset=["CODIGO_CURSO"], keep="first")
            )
        return {
            str(row["CODIGO_CURSO"]): float(row["NUMERO_CREDITOS"])
            for _, row in credits_df.iterrows()
        }

    def _build_course_to_department(self) -> dict[str, Any]:
        dept_df = (
            self.df_oferta[["CODIGO_CURSO", "CODIGO_DEPARTAMENTO"]]
            .drop_duplicates(subset=["CODIGO_CURSO"], keep="first")
            .dropna(subset=["CODIGO_CURSO"])
        )
        return {
            str(row["CODIGO_CURSO"]): row["CODIGO_DEPARTAMENTO"]
            for _, row in dept_df.iterrows()
        }

    def _build_crn_to_professor(self) -> dict[Any, Any]:
        crn_df = (
            self.df_cursos_profesores[["ID_CRN", "LOGIN_DOCENTE"]]
            .drop_duplicates(subset=["ID_CRN"], keep="first")
            .dropna(subset=["ID_CRN"])
        )
        return {
            row["ID_CRN"]: row["LOGIN_DOCENTE"]
            for _, row in crn_df.iterrows()
        }

    def get_base_features(self, student_id: str, overrides: dict[str, Any] | None = None) -> dict[str, float]:
        student_data = consultar_estudiante(student_id)
        if student_data.get("error"):
            raise ValueError(student_data["error"])

        base_features = {
            BASE_FEATURE_NAME_MAP[key]: student_data.get(key)
            for key in BASE_FEATURE_NAME_MAP
        }

        if overrides:
            for key, value in overrides.items():
                normalized_key = BASE_FEATURE_NAME_MAP.get(key, key)
                if normalized_key in self.base_feature_cols:
                    base_features[normalized_key] = value

        missing = [key for key, value in base_features.items() if value is None]
        if missing:
            raise ValueError(f"Missing base features for student {student_id}: {missing}")

        return {
            "PGA_ANTERIOR": float(base_features["PGA_ANTERIOR"]),
            "SEMESTRES_ANTERIORES": int(base_features["SEMESTRES_ANTERIORES"]),
            "PCT_CREDITOS_ANTERIOR": float(base_features["PCT_CREDITOS_ANTERIOR"]),
        }

    def get_course_credits(self, course_code: str) -> float:
        credits = self.course_to_credits.get(str(course_code))
        if credits is None:
            raise ValueError(f"Unknown credits for course {course_code}")
        if float(credits) <= 0:
            raise ValueError(f"Course {course_code} is not selectable because it has {credits} credits")
        return float(credits)

    def _resolve_period(self, period: int | None) -> int:
        if period is not None:
            return int(period)
        return int(self.latest_period) + 1

    def _compute_rates_for_period(self, period: int) -> tuple[dict[Any, float], dict[Any, float], dict[Any, float], float]:
        period_int = self._resolve_period(period)
        df_prior = self.df_cursos_profesores[self.df_cursos_profesores["PERIODO"] < period_int]
        if df_prior.empty:
            return {}, {}, {}, float("nan")
        rates_n3, rates_n2, rates_n1, global_rate = _compute_rate_tables(
            df_prior, self.df_oferta, self.thresholds,
        )
        normalized_n3 = {
            (str(course_code), professor): float(rate)
            for (course_code, professor), rate in rates_n3.items()
        }
        normalized_n2 = {
            str(course_code): float(rate)
            for course_code, rate in rates_n2.items()
        }
        normalized_n1 = {
            department: float(rate)
            for department, rate in rates_n1.items()
        }
        return normalized_n3, normalized_n2, normalized_n1, float(global_rate)

    def calculate_course_difficulties(
        self,
        course_codes: list[str],
        period: int | None = None,
        professors_by_course: dict[str, str] | None = None,
        credits_by_course: dict[str, float] | None = None,
    ) -> list[CourseDifficulty]:
        rates_n3, rates_n2, rates_n1, global_rate = self._compute_rates_for_period(period or self.latest_period + 1)
        difficulties: list[CourseDifficulty] = []

        for course_code in course_codes:
            course_key = str(course_code)
            professor = None
            if professors_by_course:
                professor = professors_by_course.get(course_key)

            difficulty_rate = None
            source_level = "GLOBAL"

            if professor is not None:
                difficulty_rate = rates_n3.get((course_key, professor))
                if difficulty_rate is not None:
                    source_level = "N3"

            if difficulty_rate is None:
                difficulty_rate = rates_n2.get(course_key)
                if difficulty_rate is not None:
                    source_level = "N2"

            if difficulty_rate is None:
                department = self.course_to_department.get(course_key)
                difficulty_rate = rates_n1.get(department)
                if difficulty_rate is not None:
                    source_level = "N1"

            if difficulty_rate is None:
                difficulty_rate = global_rate
                source_level = "GLOBAL"

            if pd.isna(difficulty_rate):
                raise ValueError(f"Could not resolve difficulty for course {course_key}")

            credits = (
                float(credits_by_course[course_key])
                if credits_by_course and course_key in credits_by_course
                else self.get_course_credits(course_key)
            )

            if float(credits) <= 0:
                raise ValueError(f"Course {course_key} is not selectable because it has {credits} credits")

            difficulties.append(
                CourseDifficulty(
                    course_code=course_key,
                    credits=credits,
                    difficulty_rate=float(difficulty_rate),
                    source_level=source_level,
                    professor=professor,
                )
            )

        return difficulties

    def aggregate_difficulty_features(self, difficulties: list[CourseDifficulty]) -> dict[str, float]:
        if not difficulties:
            raise ValueError("At least one course is required to aggregate difficulty features")

        rates = np.array([item.difficulty_rate for item in difficulties], dtype=float)
        credits = np.array([item.credits for item in difficulties], dtype=float)

        if float(credits.sum()) <= 0:
            raise ValueError("Total course credits must be positive")

        weighted_mean = float(np.average(rates, weights=credits))
        diff_min = float(np.min(rates))
        diff_std = float(np.std(rates, ddof=1)) if len(rates) > 1 else 0.0

        return {
            "DIFF_MEAN_WEIGHTED": weighted_mean,
            "DIFF_MIN": diff_min,
            "DIFF_STD": diff_std,
        }

    def build_feature_vector(
        self,
        student_id: str,
        course_codes: list[str],
        period: int | None = None,
        total_credits: float | None = None,
        professors_by_course: dict[str, str] | None = None,
        credits_by_course: dict[str, float] | None = None,
        base_feature_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not course_codes:
            raise ValueError("At least one course must be provided")

        base_features = self.get_base_features(student_id, overrides=base_feature_overrides)
        difficulties = self.calculate_course_difficulties(
            course_codes=course_codes,
            period=period,
            professors_by_course=professors_by_course,
            credits_by_course=credits_by_course,
        )
        difficulty_features = self.aggregate_difficulty_features(difficulties)

        inferred_total_credits = float(sum(item.credits for item in difficulties))
        feature_values = {
            **base_features,
            "NUM_CURSOS": len(difficulties),
            "CREDITOS_TOTALES": float(total_credits) if total_credits is not None else inferred_total_credits,
            **difficulty_features,
        }

        ordered_values = [feature_values[col] for col in self.v2_feature_cols]
        difficulty_payload = [
            {
                "course_code": item.course_code,
                "credits": item.credits,
                "difficulty_rate": item.difficulty_rate,
                "source_level": item.source_level,
                "professor": item.professor,
            }
            for item in difficulties
        ]

        return {
            "student_id": student_id,
            "period": self._resolve_period(period),
            "feature_values": feature_values,
            "feature_order": list(self.v2_feature_cols),
            "feature_vector": ordered_values,
            "difficulty_courses": difficulty_payload,
        }


@lru_cache(maxsize=1)
def get_v2_feature_service() -> V2FeatureService:
    return V2FeatureService()
