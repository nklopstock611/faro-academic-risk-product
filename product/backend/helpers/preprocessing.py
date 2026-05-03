"""Feature engineering, temporal split, and hierarchical level construction.

Pipeline summary:
  1. preprocess_materias   – filter + merge department info from oferta
  2. build_inscripciones   – aggregate to (student, period) level
  3. calcular_pga_anterior – leakage-safe PGA / semester history features
  4. build_course_mapping  – course_code -> department/faculty dict (v1)
  5. build_levels          – assign NIVEL_1 / NIVEL_2 / NIVEL_3 signatures (v1)
  5b. build_difficulty_features – hierarchical course difficulty (v2)
  6. temporal_split        – train / val / test by cutoff period
  7. prepare_dataset       – runs steps 1-6 end-to-end
"""

import numpy as np
import pandas as pd

FEATURE_COLS_BASE = [
    'PGA_ANTERIOR',
    'SEMESTRES_ANTERIORES',
    'PCT_CREDITOS_ANTERIOR',
    'NUM_CURSOS',
    'CREDITOS_TOTALES',
]

FEATURE_COLS_V2 = FEATURE_COLS_BASE + [
    'DIFF_MEAN_WEIGHTED',
    'DIFF_MIN',
    'DIFF_STD',
]

# Default: base features (v1 compat). V2 scripts import FEATURE_COLS_V2.
FEATURE_COLS = FEATURE_COLS_BASE

TARGET_COL = 'PCT_CREDITOS_APROBADOS'

STUDENT_COL = 'ID_PERSONA'


# ---------------------------------------------------------------------------
# Step 1: preprocess materias
# ---------------------------------------------------------------------------

def preprocess_materias(df_materias: pd.DataFrame, df_oferta: pd.DataFrame) -> pd.DataFrame:
    """Filter materias to pregrado/historia and merge department codes from oferta."""
    df_clean = (
        df_materias[
            (df_materias['NIVEL_ACADEMICO_ESTUDIANTE'] == 'Pregrado')
            & (df_materias['ESTATUS'] == 'HISTORIA')
            & (df_materias['RESULTADO'].isin(['APROBADO', 'REPROBADO', 'RETIRADO']))
        ]
        .assign(
            EXITO=lambda x: (x['RESULTADO'] == 'APROBADO').astype('int8'),
        )
        .copy()
    )

    # Join via ID_CRN for precise section-level matching
    df_fac = (
        df_oferta[['ID_CRN', 'CODIGO_DEPARTAMENTO', 'CODIGO_FACULTAD']]
        .drop_duplicates(subset=['ID_CRN'], keep='first')
    )

    df_clean = df_clean.merge(df_fac, on='ID_CRN', how='left')
    return df_clean


# ---------------------------------------------------------------------------
# Step 2: aggregate to student-semester level
# ---------------------------------------------------------------------------

def build_inscripciones(df_materias_clean: pd.DataFrame) -> pd.DataFrame:
    """Aggregate course-level records to student-semester level.

    Each row = one student's full enrollment in one period.
    PCT_CREDITOS_APROBADOS = fraction of credits approved that semester
                             (credit-weighted, unlike a simple course count).
    """
    df_mat = df_materias_clean.copy()
    df_mat['CREDITOS_APROBADOS'] = df_mat['NUMERO_CREDITOS'] * df_mat['EXITO']

    df = df_mat.groupby(
        [STUDENT_COL, 'PERIODO'], as_index=False
    ).agg(
        CURSOS_LISTA        =('CODIGO_CURSO',        list ),
        CREDITOS_TOTALES    =('NUMERO_CREDITOS',     'sum'),
        NUM_CURSOS          =('NUMERO_CREDITOS',     'count'),
        CREDITOS_APROBADOS  =('CREDITOS_APROBADOS',  'sum'),
    )

    df['PCT_CREDITOS_APROBADOS'] = (
        df['CREDITOS_APROBADOS'] / df['CREDITOS_TOTALES']
    )
    df['PCT_CREDITOS_PERDIDOS'] = 1 - df['PCT_CREDITOS_APROBADOS']
    return df


# ---------------------------------------------------------------------------
# Step 3: PGA features (leakage-safe)
# ---------------------------------------------------------------------------

def calcular_pga_anterior(
    df_inscripciones: pd.DataFrame,
    df_rendimiento: pd.DataFrame,
    df_info_actual: pd.DataFrame,
) -> pd.DataFrame:
    """Compute PGA_ANTERIOR, SEMESTRES_ANTERIORES, PCT_CREDITOS_ANTERIOR.

    Uses merge_asof (direction='backward', allow_exact_matches=False) so that
    only information from strictly *prior* periods is used — no data leakage.

    For students with no prior history, falls back to normalized ICFES score.
    """
    df_ins = df_inscripciones[[STUDENT_COL, 'PERIODO']].copy()
    df_ins['PERIODO_INT'] = df_ins['PERIODO'].astype(int)

    df_hist = df_rendimiento[[
        STUDENT_COL, 'PERIODO',
        'PGA', 'TOTAL_SEMESTRES_MATRICULADOS', 'PORCENTAJE_CREDITOS_APROBADOS',
    ]].copy()
    for col in ['PGA', 'TOTAL_SEMESTRES_MATRICULADOS', 'PORCENTAJE_CREDITOS_APROBADOS']:
        df_hist[col] = pd.to_numeric(df_hist[col], errors='coerce')
    df_hist['PERIODO_INT'] = df_hist['PERIODO'].astype(int)

    pct_creditos_promedio = df_hist['PORCENTAJE_CREDITOS_APROBADOS'].mean()

    df_hist = df_hist.rename(columns={
        'PERIODO_INT': 'PERIODO_HIST_INT',
        'PGA': 'PGA_HIST',
        'TOTAL_SEMESTRES_MATRICULADOS': 'SEMESTRES_HIST',
        'PORCENTAJE_CREDITOS_APROBADOS': 'PCT_CREDITOS_HIST',
    })

    df_icfes = df_info_actual[[STUDENT_COL, 'PUNTAJE_ICFES']].copy()
    df_icfes['PUNTAJE_ICFES'] = pd.to_numeric(df_icfes['PUNTAJE_ICFES'], errors='coerce')

    df_ins_sorted = df_ins.sort_values('PERIODO_INT')
    df_hist_sorted = df_hist.sort_values('PERIODO_HIST_INT')

    df_merged = pd.merge_asof(
        df_ins_sorted,
        df_hist_sorted[[STUDENT_COL, 'PERIODO_HIST_INT', 'PGA_HIST',
                         'SEMESTRES_HIST', 'PCT_CREDITOS_HIST']],
        left_on='PERIODO_INT',
        right_on='PERIODO_HIST_INT',
        by=STUDENT_COL,
        direction='backward',
        allow_exact_matches=False,
    )

    df_final = df_merged.merge(df_icfes, on=STUDENT_COL, how='left')

    tiene_historia = df_final['PGA_HIST'].notna()
    tiene_icfes = df_final['PUNTAJE_ICFES'].notna()

    df_final['PGA_ANTERIOR'] = np.nan
    df_final['SEMESTRES_ANTERIORES'] = np.nan
    df_final['PCT_CREDITOS_ANTERIOR'] = np.nan

    # Students with prior academic record
    df_final.loc[tiene_historia, 'PGA_ANTERIOR'] = df_final.loc[tiene_historia, 'PGA_HIST']
    df_final.loc[tiene_historia, 'SEMESTRES_ANTERIORES'] = df_final.loc[tiene_historia, 'SEMESTRES_HIST']
    df_final.loc[tiene_historia, 'PCT_CREDITOS_ANTERIOR'] = df_final.loc[tiene_historia, 'PCT_CREDITOS_HIST']

    # New students with only ICFES score
    mask_icfes = ~tiene_historia & tiene_icfes
    df_final.loc[mask_icfes, 'PGA_ANTERIOR'] = df_final.loc[mask_icfes, 'PUNTAJE_ICFES'] / 500.0
    df_final.loc[mask_icfes, 'SEMESTRES_ANTERIORES'] = 0
    df_final.loc[mask_icfes, 'PCT_CREDITOS_ANTERIOR'] = pct_creditos_promedio

    return df_final[[STUDENT_COL, 'PERIODO',
                      'PGA_ANTERIOR', 'SEMESTRES_ANTERIORES', 'PCT_CREDITOS_ANTERIOR']]


# ---------------------------------------------------------------------------
# Step 4: course → department mapping (v1)
# ---------------------------------------------------------------------------

def build_course_mapping(df_oferta: pd.DataFrame, use_department: bool = True) -> dict:
    """Build {course_code: category_label} dict from oferta dataset."""
    col = 'CODIGO_DEPARTAMENTO' if use_department else 'CODIGO_FACULTAD'
    prefix = 'DEPT_' if use_department else 'FAC_'
    mapping = (
        df_oferta[['CODIGO_CURSO', col]]
        .drop_duplicates(subset=['CODIGO_CURSO'], keep='first')
        .set_index('CODIGO_CURSO')[col]
        .to_dict()
    )
    return {
        k: f"{prefix}{v}" if pd.notna(v) else 'DESCONOCIDO'
        for k, v in mapping.items()
    }


# ---------------------------------------------------------------------------
# Step 5: hierarchical level assignment (v1)
# ---------------------------------------------------------------------------

def build_nivel_2_signature(cursos_lista: list, mapeo_curso_cat: dict) -> str:
    """Department composition signature: 'DEPT_A:2_DEPT_B:1' (sorted)."""
    categorias = [mapeo_curso_cat.get(str(c), 'DESCONOCIDO') for c in cursos_lista]
    contador = {}
    for cat in categorias:
        contador[cat] = contador.get(cat, 0) + 1
    return '_'.join(f"{cat}:{cnt}" for cat, cnt in sorted(contador.items()))


def build_nivel_3_signature(cursos_lista: list) -> str:
    """Exact course combination: sorted course codes joined by '_'."""
    return '_'.join(sorted(str(c) for c in cursos_lista))


def build_levels(df_inscripciones: pd.DataFrame, mapeo_curso_cat: dict) -> pd.DataFrame:
    """Assign NIVEL_1, NIVEL_2, NIVEL_3 signatures to each student-semester row."""
    df = df_inscripciones.copy()
    df['NIVEL_1'] = df['NUM_CURSOS'].astype(str)
    df['NIVEL_2'] = df['CURSOS_LISTA'].apply(
        lambda cs: build_nivel_2_signature(cs, mapeo_curso_cat)
    )
    df['NIVEL_3'] = df['CURSOS_LISTA'].apply(build_nivel_3_signature)
    return df


# ---------------------------------------------------------------------------
# Step 6: temporal split
# ---------------------------------------------------------------------------

def temporal_split(df: pd.DataFrame, train_cutoff: int, val_cutoff: int):
    """Split by PERIODO into train / val / test.

    Comparison is done on integer period values (e.g. 202010, 202310).
    """
    periodo_num = df['PERIODO'].astype(int)
    df_train = df[periodo_num <= train_cutoff].copy()
    df_val   = df[(periodo_num > train_cutoff) & (periodo_num <= val_cutoff)].copy()
    df_test  = df[periodo_num > val_cutoff].copy()
    return df_train, df_val, df_test


# ---------------------------------------------------------------------------
# Step 7: end-to-end pipeline
# ---------------------------------------------------------------------------

def prepare_dataset(
    datasets: dict,
    train_cutoff: int = 202010,
    val_cutoff: int = 202310,
    use_department: bool = True,
    version: str = 'v1',
):
    """Full preprocessing pipeline.

    version='v1': partition-based hierarchy (NIVEL_1/2/3 signatures)
    version='v2': feature-based hierarchy (DIFF_MEAN_WEIGHTED, DIFF_MIN)

    Returns: df_train, df_val, df_test, extra
      - v1: extra = mapeo_curso_cat
      - v2: extra = None
    """
    print("Step 1: Preprocessing materias...")
    df_mat_clean = preprocess_materias(datasets['materias'], datasets['oferta'])
    print(f"  {len(df_mat_clean):,} rows after filtering")

    print("Step 2: Building student-semester inscripciones...")
    df_ins = build_inscripciones(df_mat_clean)
    print(f"  {len(df_ins):,} student-semester records")

    print("Step 3: Computing PGA_ANTERIOR (leakage-safe)...")
    df_pga = calcular_pga_anterior(df_ins, datasets['rendimiento'], datasets['info_actual'])
    df_ins = df_ins.merge(
        df_pga[[STUDENT_COL, 'PERIODO',
                 'PGA_ANTERIOR', 'SEMESTRES_ANTERIORES', 'PCT_CREDITOS_ANTERIOR']],
        on=[STUDENT_COL, 'PERIODO'],
        how='left',
    )

    extra = None

    if version == 'v1':
        print("Step 4: Building course->department mapping...")
        mapeo_curso_cat = build_course_mapping(datasets['oferta'], use_department)
        print(f"  {len(mapeo_curso_cat):,} courses mapped")

        print("Step 5: Assigning hierarchical levels...")
        df_ins = build_levels(df_ins, mapeo_curso_cat)
        print(f"  NIVEL_1 groups: {df_ins['NIVEL_1'].nunique()}")
        print(f"  NIVEL_2 groups: {df_ins['NIVEL_2'].nunique():,}")
        print(f"  NIVEL_3 groups: {df_ins['NIVEL_3'].nunique():,}")
        extra = mapeo_curso_cat

    elif version == 'v2':
        from .difficulty_features import build_difficulty_features
        print("Step 4: Computing hierarchical difficulty features...")
        df_diff = build_difficulty_features(
            df_mat_clean, datasets['cursos_profesores'], datasets['oferta']
        )
        df_ins = df_ins.merge(
            df_diff, on=[STUDENT_COL, 'PERIODO'], how='left',
        )
        print(f"  DIFF_MEAN_WEIGHTED coverage: "
              f"{df_ins['DIFF_MEAN_WEIGHTED'].notna().mean()*100:.1f}%")
        print(f"  DIFF_MIN coverage: "
              f"{df_ins['DIFF_MIN'].notna().mean()*100:.1f}%")

    print("Step 6: Temporal split...")
    df_train, df_val, df_test = temporal_split(df_ins, train_cutoff, val_cutoff)
    print(f"  Train: {len(df_train):,} | Val: {len(df_val):,} | Test: {len(df_test):,}")

    return df_train, df_val, df_test, extra
