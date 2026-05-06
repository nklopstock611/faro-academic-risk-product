"""Regenerate the static autocompletion JSONs that the frontend consumes.

Reads the active parquets in ``product/backend/data/`` (auto-detecting
deanonymized vs anonymized variants via ``helpers.data_loader``) and writes:

  - codigos_estudiantes.json     : list[str] of CODIGO_ESTUDIANTE
  - codigos_cursos.json          : list[str] of CODIGO_CURSO
  - codigos_cursos_creditos.json : dict[str, float] CODIGO_CURSO -> NUMERO_CREDITOS

into ``product/frontend/academic-predictor/public/data/``.

Run after pointing the backend at a different dataset variant so the
autocomplete reflects whichever student/course IDs are actually loadable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parents[1]
FRONTEND_DATA_DIR = REPO_ROOT / "product" / "frontend" / "academic-predictor" / "public" / "data"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from helpers.data_loader import resolve_dataset_path  # noqa: E402


def collect_unique_strings(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    series = df[column].dropna().astype(str).str.strip()
    return [value for value in series.unique().tolist() if value]


def main() -> int:
    data_dir = BACKEND_DIR / "data"
    if not data_dir.exists():
        print(f"ERROR: data directory not found: {data_dir}", file=sys.stderr)
        return 1
    if not FRONTEND_DATA_DIR.exists():
        FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)

    student_sources = [
        "informacion_actual_estudiante",
        "historial_rendimiento_academico_estudiante",
        "historial_materias_estudiante",
    ]
    course_sources = [
        "oferta_academica",
        "historial_materias_estudiante",
    ]

    student_codes: set[str] = set()
    for base in student_sources:
        path = resolve_dataset_path(data_dir, base)
        if path is None:
            print(f"  [skip] no parquet for {base}")
            continue
        df = pd.read_parquet(path, columns=["CODIGO_ESTUDIANTE"])
        added = collect_unique_strings(df, "CODIGO_ESTUDIANTE")
        student_codes.update(added)
        print(f"  [{base}] +{len(added):,} estudiantes (path={path.name})")

    course_codes: set[str] = set()
    for base in course_sources:
        path = resolve_dataset_path(data_dir, base)
        if path is None:
            print(f"  [skip] no parquet for {base}")
            continue
        df = pd.read_parquet(path, columns=["CODIGO_CURSO"])
        added = collect_unique_strings(df, "CODIGO_CURSO")
        course_codes.update(added)
        print(f"  [{base}] +{len(added):,} cursos (path={path.name})")

    credits_map: dict[str, float] = {}
    materias_path = resolve_dataset_path(data_dir, "historial_materias_estudiante")
    if materias_path is None:
        print("ERROR: historial_materias_estudiante parquet is required for credits", file=sys.stderr)
        return 2
    materias_df = pd.read_parquet(materias_path, columns=["CODIGO_CURSO", "NUMERO_CREDITOS"])
    materias_df = materias_df.dropna(subset=["CODIGO_CURSO", "NUMERO_CREDITOS"])
    materias_df["CODIGO_CURSO"] = materias_df["CODIGO_CURSO"].astype(str).str.strip()
    materias_df = materias_df.drop_duplicates(subset=["CODIGO_CURSO"], keep="first")
    for _, row in materias_df.iterrows():
        credits_map[row["CODIGO_CURSO"]] = float(row["NUMERO_CREDITOS"])

    students_sorted = sorted(student_codes)
    courses_sorted = sorted(course_codes)
    credits_sorted = {code: credits_map[code] for code in courses_sorted if code in credits_map}

    outputs = {
        "codigos_estudiantes.json": students_sorted,
        "codigos_cursos.json": courses_sorted,
        "codigos_cursos_creditos.json": credits_sorted,
    }

    for filename, payload in outputs.items():
        out_path = FRONTEND_DATA_DIR / filename
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        size_kb = out_path.stat().st_size / 1024
        count = len(payload) if hasattr(payload, "__len__") else 0
        print(f"  wrote {filename}: {count:,} entries ({size_kb:,.0f} KB)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
