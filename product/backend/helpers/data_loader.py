"""Load raw parquet datasets from data directory."""
from pathlib import Path
import pandas as pd


DATASET_FILES = {
    'materias':    'historial_materias_estudiante_anonymized.parquet',
    'rendimiento': 'historial_rendimiento_academico_estudiante_anonymized.parquet',
    'percentiles': 'percentiles_academicos_estudiante_anonymized.parquet',
    'riesgos':     'riesgos_historicos_estudiante_pregrado_anonymized.parquet',
    'oferta':      'oferta_academica_anonymized.parquet',
    'info_actual': 'informacion_actual_estudiante_anonymized.parquet',
    'financiera':  'informacion_financiera_estudiante_anonymized.parquet',
    'horarios':    'horarios_curso_anonymized.parquet',
    'estados':     'historial_estados_academicos_estudiante_anonymized.parquet',
    'cursos_profesores':       'cursos_dictados_profesores_anonymized.parquet',
    'rendimiento_profesores':  'historial_rendimiento_profesores_anonymized.parquet',
}

REQUIRED = {'materias', 'rendimiento', 'oferta', 'info_actual', 'cursos_profesores'}


def load_datasets(data_dir: str) -> dict:
    """Load parquet datasets from data_dir. Returns dict of DataFrames.

    Required: materias, rendimiento, oferta, info_actual.
    Others are loaded if present but not required.
    """
    data_dir = Path(data_dir)
    datasets = {}
    for key, filename in DATASET_FILES.items():
        path = data_dir / filename
        if path.exists():
            datasets[key] = pd.read_parquet(path)
            print(f"  [{key}] {len(datasets[key]):,} rows")
        elif key in REQUIRED:
            raise FileNotFoundError(f"Required dataset not found: {path}")
        else:
            print(f"  [{key}] not found, skipping")
    return datasets
