"""Hierarchical course difficulty features with cascading fallback.

Computes per-student-semester features encoding how difficult their course
load is, based on historical approval rates at three levels of granularity:

  NIVEL_3: course + professor (most specific, requires ≥20 historical students)
  NIVEL_2: course regardless of professor (requires ≥10 historical students)
  NIVEL_1: department (always available)

Fallback: if a course lacks sufficient data at a given level, the next
coarser level is used. This guarantees every course gets a difficulty
estimate while using the most specific information available.

Leakage safety: all rates are computed from strictly prior periods only.
"""

import numpy as np
import pandas as pd

STUDENT_COL = 'CODIGO_ESTUDIANTE'

DEFAULT_THRESHOLDS = {'NIVEL_3': 20, 'NIVEL_2': 10, 'NIVEL_1': 5}

# Section is identified by (PERIODO, CODIGO_CURSO, SECCION). This works for
# both anonymized and non-anonymized datasets — no dependency on ID_CRN.
SECTION_KEY_COLS = ['PERIODO', 'CODIGO_CURSO', 'SECCION']


def _compute_rate_tables(df_cursos_hist, df_oferta, thresholds):
    """Compute approval rate lookup tables from historical course data.

    Parameters
    ----------
    df_cursos_hist : DataFrame
        Rows from cursos_dictados_profesores for STRICTLY PRIOR periods.
    df_oferta : DataFrame
        Course catalog with CODIGO_DEPARTAMENTO.
    thresholds : dict
        Minimum cumulative students per level.

    Returns
    -------
    rates_n3 : dict  {(CODIGO_CURSO, LOGIN_DOCENTE): rate}
    rates_n2 : dict  {CODIGO_CURSO: rate}
    rates_n1 : dict  {CODIGO_DEPARTAMENTO: rate}
    global_rate : float
    """
    if len(df_cursos_hist) == 0:
        return {}, {}, {}, np.nan

    # Filter to rows with valid approval data
    df = df_cursos_hist.dropna(subset=['TASA_APROBACION']).copy()
    df = df[df['TOTAL_ESTUDIANTES'] > 0]

    if len(df) == 0:
        return {}, {}, {}, np.nan

    # Global rate (weighted by students)
    global_rate = float(
        np.average(df['TASA_APROBACION'], weights=df['TOTAL_ESTUDIANTES'])
    )

    # Precompute weighted product for fast weighted-mean aggregation
    df = df.copy()
    df['_WP'] = df['TASA_APROBACION'] * df['TOTAL_ESTUDIANTES']

    # NIVEL_3: course + professor (weighted mean across periods)
    n3 = df.groupby(['CODIGO_CURSO', 'LOGIN_DOCENTE']).agg(
        wp_sum=('_WP', 'sum'),
        total=('TOTAL_ESTUDIANTES', 'sum'),
    )
    n3_valid = n3[n3['total'] >= thresholds['NIVEL_3']]
    n3_valid = n3_valid.assign(rate=n3_valid['wp_sum'] / n3_valid['total'])
    rates_n3 = n3_valid['rate'].to_dict()

    # NIVEL_2: course regardless of professor
    n2 = df.groupby('CODIGO_CURSO').agg(
        wp_sum=('_WP', 'sum'),
        total=('TOTAL_ESTUDIANTES', 'sum'),
    )
    n2_valid = n2[n2['total'] >= thresholds['NIVEL_2']]
    n2_valid = n2_valid.assign(rate=n2_valid['wp_sum'] / n2_valid['total'])
    rates_n2 = n2_valid['rate'].to_dict()

    # NIVEL_1: department (join cursos → oferta for department)
    curso_dept = (
        df_oferta[['CODIGO_CURSO', 'CODIGO_DEPARTAMENTO']]
        .drop_duplicates(subset=['CODIGO_CURSO'], keep='first')
        .set_index('CODIGO_CURSO')['CODIGO_DEPARTAMENTO']
        .to_dict()
    )
    df['DEPT'] = df['CODIGO_CURSO'].map(curso_dept)
    dept_data = df.dropna(subset=['DEPT'])
    if len(dept_data) > 0:
        n1 = dept_data.groupby('DEPT').agg(
            wp_sum=('_WP', 'sum'),
            total=('TOTAL_ESTUDIANTES', 'sum'),
        )
        n1 = n1.assign(rate=n1['wp_sum'] / n1['total'])
        rates_n1 = n1['rate'].to_dict()
    else:
        rates_n1 = {}

    return rates_n3, rates_n2, rates_n1, global_rate


def _assign_difficulty(row, rates_n3, rates_n2, rates_n1,
                       curso_dept, global_rate):
    """Assign difficulty rate to a single course enrollment with cascading fallback.

    Returns (rate, level_used).
    """
    curso = row['CODIGO_CURSO']
    prof = row.get('LOGIN_DOCENTE')

    # Try NIVEL_3: course + professor
    if prof is not None and not (isinstance(prof, float) and pd.isna(prof)):
        key = (curso, prof)
        if key in rates_n3:
            return rates_n3[key], 'NIVEL_3'

    # Try NIVEL_2: course only
    if curso in rates_n2:
        return rates_n2[curso], 'NIVEL_2'

    # Try NIVEL_1: department
    dept = curso_dept.get(curso)
    if dept is not None and dept in rates_n1:
        return rates_n1[dept], 'NIVEL_1'

    # Final fallback: global
    return global_rate, 'GLOBAL'


def build_difficulty_features(
    df_materias_clean: pd.DataFrame,
    df_cursos_profesores: pd.DataFrame,
    df_oferta: pd.DataFrame,
    thresholds: dict = None,
) -> pd.DataFrame:
    """Build semester-level difficulty features from course-level approval rates.

    For each student-semester, computes:
      DIFF_MEAN_WEIGHTED: credit-weighted mean approval rate of their courses
      DIFF_MIN: minimum approval rate across their courses (hardest course)

    All rates are leakage-safe (computed from strictly prior periods).

    Parameters
    ----------
    df_materias_clean : DataFrame
        Output of preprocess_materias (filtered).
    df_cursos_profesores : DataFrame
        Per-section course stats with TASA_APROBACION and LOGIN_DOCENTE.
    df_oferta : DataFrame
        Course catalog with CODIGO_DEPARTAMENTO.
    thresholds : dict
        Minimum students per level for rate to be considered reliable.

    Returns
    -------
    DataFrame with columns: [CODIGO_ESTUDIANTE, PERIODO, DIFF_MEAN_WEIGHTED, DIFF_MIN, DIFF_STD]
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    # Enrich materias with LOGIN_DOCENTE via the stable section key
    # (PERIODO, CODIGO_CURSO, SECCION). This avoids any dependency on ID_CRN.
    if 'LOGIN_DOCENTE' not in df_materias_clean.columns:
        prof_lookup = (
            df_cursos_profesores[SECTION_KEY_COLS + ['LOGIN_DOCENTE']]
            .dropna(subset=SECTION_KEY_COLS)
            .drop_duplicates(subset=SECTION_KEY_COLS, keep='first')
        )
        df_materias_clean = df_materias_clean.merge(
            prof_lookup, on=SECTION_KEY_COLS, how='left',
        )

    # Course → department lookup
    curso_dept = (
        df_oferta[['CODIGO_CURSO', 'CODIGO_DEPARTAMENTO']]
        .drop_duplicates(subset=['CODIGO_CURSO'], keep='first')
        .set_index('CODIGO_CURSO')['CODIGO_DEPARTAMENTO']
        .to_dict()
    )

    # Process period by period (sorted) for leakage safety
    periodos = sorted(df_materias_clean['PERIODO'].unique(), key=lambda x: int(x))
    all_rows = []
    total_by_level = {'NIVEL_3': 0, 'NIVEL_2': 0, 'NIVEL_1': 0, 'GLOBAL': 0}

    rates_n3, rates_n2, rates_n1, global_rate = {}, {}, {}, np.nan

    # Pre-convert PERIODO to int for fast comparison
    cursos_prof_periodo_int = df_cursos_profesores['PERIODO'].astype(int)
    min_prof_periodo = int(cursos_prof_periodo_int.min())
    prev_periodo_int = None

    for i, periodo in enumerate(periodos):
        periodo_int = int(periodo)

        # Only recompute rates when there's new professor data to include
        if periodo_int > min_prof_periodo and periodo_int != prev_periodo_int:
            df_prior = df_cursos_profesores[cursos_prof_periodo_int < periodo_int]
            if len(df_prior) > 0:
                rates_n3, rates_n2, rates_n1, global_rate = _compute_rate_tables(
                    df_prior, df_oferta, thresholds
                )
        prev_periodo_int = periodo_int

        # Get all course enrollments for this period
        mask_periodo = df_materias_clean['PERIODO'] == periodo
        df_period = df_materias_clean[mask_periodo].copy()

        if len(df_period) == 0:
            continue

        # Vectorized difficulty assignment (avoid row-by-row apply)
        # LOGIN_DOCENTE was already merged into df_materias_clean above.
        df_period['_PROF'] = df_period.get('LOGIN_DOCENTE')
        df_period['_DEPT'] = df_period['CODIGO_CURSO'].map(curso_dept)

        # Step 2: look up rates at each level
        if rates_n3:
            df_period['_RATE_N3'] = [
                rates_n3.get((c, p)) if p is not None else None
                for c, p in zip(df_period['CODIGO_CURSO'], df_period['_PROF'])
            ]
        else:
            df_period['_RATE_N3'] = None

        df_period['_RATE_N2'] = df_period['CODIGO_CURSO'].map(
            rates_n2 if rates_n2 else {}
        )
        df_period['_RATE_N1'] = df_period['_DEPT'].map(
            rates_n1 if rates_n1 else {}
        )

        # Step 3: cascading fallback
        df_period['DIFF_RATE'] = df_period['_RATE_N3']
        df_period['DIFF_LEVEL'] = np.where(df_period['DIFF_RATE'].notna(), 'NIVEL_3', None)

        mask_no_n3 = df_period['DIFF_RATE'].isna()
        df_period.loc[mask_no_n3, 'DIFF_RATE'] = df_period.loc[mask_no_n3, '_RATE_N2']
        df_period.loc[mask_no_n3 & df_period['DIFF_RATE'].notna(), 'DIFF_LEVEL'] = 'NIVEL_2'

        mask_no_n2 = df_period['DIFF_RATE'].isna()
        df_period.loc[mask_no_n2, 'DIFF_RATE'] = df_period.loc[mask_no_n2, '_RATE_N1']
        df_period.loc[mask_no_n2 & df_period['DIFF_RATE'].notna(), 'DIFF_LEVEL'] = 'NIVEL_1'

        mask_no_n1 = df_period['DIFF_RATE'].isna()
        df_period.loc[mask_no_n1, 'DIFF_RATE'] = global_rate
        df_period.loc[mask_no_n1, 'DIFF_LEVEL'] = 'GLOBAL'

        df_period['DIFF_RATE'] = df_period['DIFF_RATE'].astype(float)

        # Clean up temp columns
        df_period.drop(columns=['_PROF', '_DEPT', '_RATE_N3', '_RATE_N2', '_RATE_N1'],
                       inplace=True)

        # Aggregate to student-semester level (vectorized)
        df_period['_WP_DIFF'] = df_period['DIFF_RATE'] * df_period['NUMERO_CREDITOS']
        grouped = df_period.groupby([STUDENT_COL, 'PERIODO'])
        df_sem = grouped.agg(
            _wp_sum=('_WP_DIFF', 'sum'),
            _cred_sum=('NUMERO_CREDITOS', 'sum'),
            DIFF_MIN=('DIFF_RATE', 'min'),
            DIFF_STD=('DIFF_RATE', 'std'),
        ).reset_index()
        df_sem['DIFF_MEAN_WEIGHTED'] = df_sem['_wp_sum'] / df_sem['_cred_sum']
        df_sem['DIFF_STD'] = df_sem['DIFF_STD'].fillna(0.0)
        df_sem.drop(columns=['_wp_sum', '_cred_sum'], inplace=True)
        all_rows.append(df_sem)

        # Progress
        n3_count = int((df_period['DIFF_LEVEL'] == 'NIVEL_3').sum())
        n2_count = int((df_period['DIFF_LEVEL'] == 'NIVEL_2').sum())
        n1_count = int((df_period['DIFF_LEVEL'] == 'NIVEL_1').sum())
        gl_count = int((df_period['DIFF_LEVEL'] == 'GLOBAL').sum())
        total_by_level['NIVEL_3'] += n3_count
        total_by_level['NIVEL_2'] += n2_count
        total_by_level['NIVEL_1'] += n1_count
        total_by_level['GLOBAL'] += gl_count
        total = len(df_period)
        # Only log periods with professor data (200010+) and not every single one
        if periodo_int >= min_prof_periodo and (i % 5 == 0 or i == len(periodos) - 1):
            print(f"    Period {periodo}: {total:,} courses — "
                  f"N3:{n3_count} N2:{n2_count} N1:{n1_count} G:{gl_count}")

    # Global distribution summary
    grand_total = sum(total_by_level.values())
    if grand_total > 0:
        print(f"\n    Overall level distribution ({grand_total:,} course enrollments):")
        for lvl in ['NIVEL_3', 'NIVEL_2', 'NIVEL_1', 'GLOBAL']:
            c = total_by_level[lvl]
            print(f"      {lvl}: {c:>10,} ({c/grand_total*100:5.1f}%)")

    if not all_rows:
        return pd.DataFrame(columns=[STUDENT_COL, 'PERIODO',
                                      'DIFF_MEAN_WEIGHTED', 'DIFF_MIN', 'DIFF_STD'])

    return pd.concat(all_rows, ignore_index=True)
