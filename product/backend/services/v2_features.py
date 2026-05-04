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

DIFFICULTY_LEVEL_LEGEND = {
    "N3": "Curso con CRN de seccion especifico, que identifica al profesor",
    "N2": "Curso en general",
    "N1": "Departamento del curso",
    "GLOBAL": "Promedio historico global",
}


@dataclass
class CourseSelection:
    course_code: str
    crn: str | None = None


@dataclass
class CourseDifficulty:
    course_code: str
    crn: str | None
    credits: float
    difficulty_rate: float
    source_level: str
    professor: str | None = None


class V2FeatureService:
    """Builds model features and interpretability payloads from backend inputs."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir or BACKEND_DIR / "data")
        self.datasets = load_datasets(str(self.data_dir))
        self.thresholds = dict(DEFAULT_THRESHOLDS)

        self.df_materias = self._get_dataset("materias", "historial_materias", "materias_estudiante").copy()
        self.df_cursos_profesores = self._get_dataset(
            "cursos_profesores",
            "curso_profesores",
            "historial_cursos_profesores",
        ).copy()
        self.df_oferta = self._get_dataset("oferta", "oferta_academica").copy()
        self.df_rendimiento = self._get_dataset("rendimiento", "historial_rendimiento", "rendimiento_estudiante").copy()

        self.df_materias["PERIODO"] = self.df_materias["PERIODO"].astype(int)
        self.df_cursos_profesores["PERIODO"] = self.df_cursos_profesores["PERIODO"].astype(int)
        self.df_rendimiento["PERIODO"] = self.df_rendimiento["PERIODO"].astype(int)

        self.df_materias["CODIGO_CURSO"] = self.df_materias["CODIGO_CURSO"].astype(str)
        self.df_cursos_profesores["CODIGO_CURSO"] = self.df_cursos_profesores["CODIGO_CURSO"].astype(str)
        self.df_oferta["CODIGO_CURSO"] = self.df_oferta["CODIGO_CURSO"].astype(str)

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

    def _normalize_optional_text(self, value: Any) -> str | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        text = str(value).strip()
        return text or None

    def _normalize_id_repr(self, value: Any) -> str | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, (bytes, bytearray)):
            return value.hex()
        text = str(value).strip()
        return text or None

    def _normalize_course_selections(
        self,
        courses: list[str | dict[str, Any] | CourseSelection],
    ) -> list[CourseSelection]:
        normalized: list[CourseSelection] = []
        for item in courses:
            if isinstance(item, CourseSelection):
                normalized.append(
                    CourseSelection(
                        course_code=str(item.course_code).strip(),
                        crn=self._normalize_optional_text(item.crn),
                    )
                )
                continue

            if isinstance(item, str):
                normalized.append(CourseSelection(course_code=item.strip(), crn=None))
                continue

            if hasattr(item, "course_code"):
                normalized.append(
                    CourseSelection(
                        course_code=str(getattr(item, "course_code")).strip(),
                        crn=self._normalize_optional_text(getattr(item, "crn", None)),
                    )
                )
                continue

            course_code = str(item.get("course_code", "")).strip()
            if not course_code:
                raise ValueError("Each course selection must include course_code")
            normalized.append(
                CourseSelection(
                    course_code=course_code,
                    crn=self._normalize_optional_text(item.get("crn")),
                )
            )

        if not normalized:
            raise ValueError("At least one course must be provided")

        return normalized

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

    def _build_crn_to_professor(self) -> dict[str, Any]:
        crn_df = self.df_cursos_profesores[["ID_CRN", "LOGIN_DOCENTE"]].dropna(subset=["ID_CRN"]).copy()
        crn_df["CRN_KEY"] = crn_df["ID_CRN"].map(self._normalize_id_repr)
        crn_df = crn_df.drop_duplicates(subset=["CRN_KEY"], keep="first")
        return {
            row["CRN_KEY"]: row["LOGIN_DOCENTE"]
            for _, row in crn_df.iterrows()
            if row["CRN_KEY"] is not None
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

    def _compute_rates_for_period(
        self,
        period: int,
    ) -> tuple[dict[Any, float], dict[Any, float], dict[Any, float], float]:
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

    def _resolve_professor_for_selection(self, selection: CourseSelection) -> str | None:
        if not selection.crn:
            return None
        return self.crn_to_professor.get(selection.crn)

    def calculate_course_difficulties(
        self,
        course_selections: list[CourseSelection],
        period: int | None = None,
        professors_by_course: dict[str, str] | None = None,
        credits_by_course: dict[str, float] | None = None,
    ) -> list[CourseDifficulty]:
        rates_n3, rates_n2, rates_n1, global_rate = self._compute_rates_for_period(period or self.latest_period + 1)
        difficulties: list[CourseDifficulty] = []

        for selection in course_selections:
            course_key = str(selection.course_code)
            professor = None
            if professors_by_course:
                professor = professors_by_course.get(course_key)
            if professor is None:
                professor = self._resolve_professor_for_selection(selection)

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
                    crn=selection.crn,
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

    def _build_match_summary(self, matches: pd.DataFrame, match_scope: str, requested_with_sections: bool) -> dict[str, Any]:
        approved_distribution = self._build_approved_pct_distribution(matches)
        return {
            "match_scope": match_scope,
            "requested_with_sections": requested_with_sections,
            "matches_found": int(len(matches)),
            "avg_semester_credits": (
                None if matches.empty else float(matches["CREDITOS_SEMESTRE"].dropna().mean())
            ),
            "avg_semester_gpa": (
                None if matches.empty else float(matches["PROMEDIO_SEMESTRAL"].dropna().mean())
            ),
            "median_semester_gpa": (
                None if matches.empty else float(matches["PROMEDIO_SEMESTRAL"].dropna().median())
            ),
            "avg_approved_pct": (
                None if matches.empty else float(matches["PORCENTAJE_CREDITOS_APROBADOS_SEMESTRE"].dropna().mean())
            ),
            "avg_cumulative_gpa": (
                None if matches.empty else float(matches["PGA"].dropna().mean())
            ),
            "approved_pct_distribution": approved_distribution,
        }

    def _build_approved_pct_distribution(self, matches: pd.DataFrame) -> list[dict[str, Any]]:
        bins = [
            ("0-20%", 0.0, 0.2),
            ("20-40%", 0.2, 0.4),
            ("40-60%", 0.4, 0.6),
            ("60-80%", 0.6, 0.8),
            ("80-100%", 0.8, 1.000001),
        ]
        values = matches["PORCENTAJE_CREDITOS_APROBADOS_SEMESTRE"].dropna()
        distribution: list[dict[str, Any]] = []
        for label, start, end in bins:
            count = int(((values >= start) & (values < end)).sum())
            distribution.append({
                "label": label,
                "count": count,
            })
        return distribution

    def get_historical_combination_summary(
        self,
        course_selections: list[CourseSelection],
        period: int | None = None,
    ) -> dict[str, Any]:
        resolved_period = self._resolve_period(period)
        selected_codes = sorted({selection.course_code for selection in course_selections})
        course_signature = "|".join(selected_codes)
        semester_courses = self.df_materias[
            self.df_materias["CODIGO_CURSO"].isin(selected_codes)
            & (self.df_materias["PERIODO"] < resolved_period)
        ][["ID_PERSONA", "PERIODO", "CODIGO_CURSO", "SECCION", "ID_CRN"]].copy()
        semester_courses["SECTION_KEY"] = semester_courses["SECCION"].map(self._normalize_optional_text)
        semester_courses["CRN_KEY"] = semester_courses["ID_CRN"].map(self._normalize_id_repr)

        grouped = (
            semester_courses.groupby(["ID_PERSONA", "PERIODO"], sort=False)
            .agg(
                COURSE_CODES=("CODIGO_CURSO", lambda values: tuple(sorted({str(value) for value in values}))),
                SECTION_PAIR_SET=(
                    "SECCION",
                    lambda _: set(),
                ),
                CRN_PAIR_SET=(
                    "ID_CRN",
                    lambda _: set(),
                ),
            )
            .reset_index()
        )

        pair_summary = (
            semester_courses.groupby(["ID_PERSONA", "PERIODO"], sort=False)
            .apply(
                lambda frame: pd.Series(
                    {
                        "SECTION_PAIR_SET": {
                            f"{row.CODIGO_CURSO}::{row.SECTION_KEY}"
                            for row in frame.itertuples()
                            if row.SECTION_KEY
                        },
                        "CRN_PAIR_SET": {
                            f"{row.CODIGO_CURSO}::{row.CRN_KEY}"
                            for row in frame.itertuples()
                            if row.CRN_KEY
                        },
                    }
                )
            )
            .reset_index()
        )

        grouped = grouped.drop(columns=["SECTION_PAIR_SET", "CRN_PAIR_SET"]).merge(
            pair_summary,
            on=["ID_PERSONA", "PERIODO"],
            how="left",
        )
        grouped["COURSE_SIGNATURE"] = grouped["COURSE_CODES"].map(lambda values: "|".join(values))
        course_matches = grouped[grouped["COURSE_SIGNATURE"] == course_signature]

        outcome_cols = [
            "ID_PERSONA",
            "PERIODO",
            "PROMEDIO_SEMESTRAL",
            "PORCENTAJE_CREDITOS_APROBADOS_SEMESTRE",
            "CREDITOS_APROBADOS_SEMESTRE",
            "CREDITOS_REPROBADOS_SEMESTRE",
            "CREDITOS_INCOMPLETOS_SEMESTRE",
            "CREDITOS_RETIRADOS_SEMESTRE",
            "CREDITOS_PENDIENTES_SEMESTRE",
            "CREDITOS_HOMOLOGADOS_SEMESTRE",
            "PGA",
        ]
        course_matches = course_matches.merge(
            self.df_rendimiento[outcome_cols],
            on=["ID_PERSONA", "PERIODO"],
            how="left",
        )
        course_matches["CREDITOS_SEMESTRE"] = course_matches[
            [
                "CREDITOS_APROBADOS_SEMESTRE",
                "CREDITOS_REPROBADOS_SEMESTRE",
                "CREDITOS_INCOMPLETOS_SEMESTRE",
                "CREDITOS_RETIRADOS_SEMESTRE",
                "CREDITOS_PENDIENTES_SEMESTRE",
                "CREDITOS_HOMOLOGADOS_SEMESTRE",
            ]
        ].sum(axis=1, min_count=1)

        section_summary = None
        requested_section_pairs = {
            f"{selection.course_code}::{selection.crn}"
            for selection in course_selections
            if selection.crn
        }
        if requested_section_pairs:
            section_matches = course_matches[
                course_matches.apply(
                    lambda row: requested_section_pairs.issubset(row["SECTION_PAIR_SET"])
                    or requested_section_pairs.issubset(row["CRN_PAIR_SET"]),
                    axis=1,
                )
            ]
            section_summary = self._build_match_summary(
                section_matches,
                match_scope="section",
                requested_with_sections=True,
            )

        course_summary = self._build_match_summary(
            course_matches,
            match_scope="course",
            requested_with_sections=bool(requested_section_pairs),
        )

        return {
            "section_match": section_summary,
            "course_match": course_summary,
        }

    def build_feature_vector(
        self,
        student_id: str,
        course_codes: list[str | dict[str, Any] | CourseSelection],
        period: int | None = None,
        total_credits: float | None = None,
        professors_by_course: dict[str, str] | None = None,
        credits_by_course: dict[str, float] | None = None,
        base_feature_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        course_selections = self._normalize_course_selections(course_codes)

        base_features = self.get_base_features(student_id, overrides=base_feature_overrides)
        difficulties = self.calculate_course_difficulties(
            course_selections=course_selections,
            period=period,
            professors_by_course=professors_by_course,
            credits_by_course=credits_by_course,
        )
        difficulty_features = self.aggregate_difficulty_features(difficulties)
        historical_combination_summary = self.get_historical_combination_summary(
            course_selections,
            period=period,
        )

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
                "crn": item.crn,
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
            "course_selection": [
                {
                    "course_code": selection.course_code,
                    "crn": selection.crn,
                }
                for selection in course_selections
            ],
            "feature_values": feature_values,
            "feature_order": list(self.v2_feature_cols),
            "feature_vector": ordered_values,
            "difficulty_courses": difficulty_payload,
            "difficulty_level_legend": dict(DIFFICULTY_LEVEL_LEGEND),
            "historical_combination_summary": historical_combination_summary,
        }


@lru_cache(maxsize=1)
def get_v2_feature_service() -> V2FeatureService:
    return V2FeatureService()
