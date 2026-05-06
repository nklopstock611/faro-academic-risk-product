"""Load raw parquet datasets from data directory.

Each dataset has a stable base name (e.g. ``historial_materias_estudiante``).
The loader probes both the non-anonymized variant (``<base>.parquet``) and
the anonymized one (``<base>_anonymized.parquet``) in that order, so the
same code works with either dataset variant without configuration.
"""
from pathlib import Path
import pandas as pd


DATASET_BASES = {
    'materias':                'historial_materias_estudiante',
    'rendimiento':             'historial_rendimiento_academico_estudiante',
    'percentiles':             'percentiles_academicos_estudiante',
    'riesgos':                 'riesgos_historicos_estudiante_pregrado',
    'oferta':                  'oferta_academica',
    'info_actual':             'informacion_actual_estudiante',
    'financiera':              'informacion_financiera_estudiante',
    'horarios':                'horarios_curso',
    'estados':                 'historial_estados_academicos_estudiante',
    'cursos_profesores':       'cursos_dictados_profesores',
    'rendimiento_profesores':  'historial_rendimiento_profesores',
}

REQUIRED = {'materias', 'rendimiento', 'oferta', 'info_actual', 'cursos_profesores'}

# Probed in order: deanonymized wins when both variants are present.
VARIANT_SUFFIXES = ['_deanonymized', '_anonymized']


def resolve_dataset_path(data_dir: Path, base: str) -> Path | None:
    """Return the first existing variant of <base>.parquet in ``data_dir``."""
    for suffix in VARIANT_SUFFIXES:
        candidate = data_dir / f'{base}{suffix}.parquet'
        if candidate.exists():
            return candidate
    return None


def load_datasets(data_dir: str) -> dict:
    """Load parquet datasets from data_dir. Returns dict of DataFrames.

    Required: materias, rendimiento, oferta, info_actual, cursos_profesores.
    Others are loaded if present but not required.
    """
    data_dir = Path(data_dir)
    datasets = {}
    for key, base in DATASET_BASES.items():
        path = resolve_dataset_path(data_dir, base)
        if path is not None:
            datasets[key] = pd.read_parquet(path)
            print(f"  [{key}] {len(datasets[key]):,} rows  ({path.name})")
        elif key in REQUIRED:
            tried = ', '.join(f'{base}{s}.parquet' for s in VARIANT_SUFFIXES)
            raise FileNotFoundError(
                f"Required dataset '{key}' not found in {data_dir}. Tried: {tried}"
            )
        else:
            print(f"  [{key}] not found, skipping")
    return datasets
