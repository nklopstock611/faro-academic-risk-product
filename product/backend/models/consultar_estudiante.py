import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

df_rendimiento = pd.read_parquet('models/historial_rendimiento_academico_estudiante_anonymized.parquet')
df_info_actual = pd.read_parquet('models/informacion_actual_estudiante_anonymized.parquet')

df_rendimiento['PERIODO'] = df_rendimiento['PERIODO'].astype(int)
df_info_actual['PERIODO'] = df_info_actual['PERIODO'].astype(int)

def consultar_estudiante(codigo_estudiante):
    estudiante_rendimiento = df_rendimiento[df_rendimiento['CODIGO_ESTUDIANTE'] == codigo_estudiante]

    if len(estudiante_rendimiento) == 0:
        estudiante_icfes = df_info_actual[df_info_actual['CODIGO_ESTUDIANTE'] == codigo_estudiante]

        if len(estudiante_icfes) == 0:
            return {
                'error': 'Estudiante no encontrado',
                'codigo_estudiante': codigo_estudiante
            }

        puntaje_icfes = estudiante_icfes['PUNTAJE_ICFES'].iloc[0]

        if pd.isna(puntaje_icfes):
            return {
                'codigo_estudiante': codigo_estudiante,
                'periodo': None,
                'pga_anterior': None,
                'semestres_anteriores': None,
                'pct_creditos_anterior': None,
                'fuente_pga': 'SIN_DATOS'
            }

        try:
            puntaje_num = float(str(puntaje_icfes).replace(',', '.'))
            icfes_normalizado = (puntaje_num / 500.0) * 5.0
        except:
            icfes_normalizado = None

        pct_creditos_promedio = df_rendimiento['PORCENTAJE_CREDITOS_APROBADOS'].mean()

        return {
            'codigo_estudiante': codigo_estudiante,
            'periodo': None,
            'pga_anterior': float(icfes_normalizado) if icfes_normalizado else None,
            'semestres_anteriores': 0,
            'pct_creditos_anterior': float(pct_creditos_promedio),
            'fuente_pga': 'ICFES_NORMALIZADO',
            'periodo_fuente': None
        }

    estudiante_rendimiento_sorted = estudiante_rendimiento.sort_values('PERIODO')
    periodo_mas_reciente = estudiante_rendimiento_sorted['PERIODO'].max()

    periodos_anteriores = estudiante_rendimiento_sorted[
        estudiante_rendimiento_sorted['PERIODO'] < periodo_mas_reciente
    ]

    if len(periodos_anteriores) == 0:
        estudiante_icfes = df_info_actual[df_info_actual['CODIGO_ESTUDIANTE'] == codigo_estudiante]

        if len(estudiante_icfes) > 0:
            puntaje_icfes = estudiante_icfes['PUNTAJE_ICFES'].iloc[0]

            if pd.notna(puntaje_icfes):
                try:
                    puntaje_num = float(str(puntaje_icfes).replace(',', '.'))
                    icfes_normalizado = (puntaje_num / 500.0) * 5.0
                except:
                    icfes_normalizado = None

                pct_creditos_promedio = df_rendimiento['PORCENTAJE_CREDITOS_APROBADOS'].mean()

                return {
                    'codigo_estudiante': codigo_estudiante,
                    'periodo': int(periodo_mas_reciente),
                    'pga_anterior': float(icfes_normalizado) if icfes_normalizado else None,
                    'semestres_anteriores': 0,
                    'pct_creditos_anterior': float(pct_creditos_promedio),
                    'fuente_pga': 'ICFES_NORMALIZADO',
                    'periodo_fuente': None
                }

        return {
            'codigo_estudiante': codigo_estudiante,
            'periodo': int(periodo_mas_reciente),
            'pga_anterior': None,
            'semestres_anteriores': None,
            'pct_creditos_anterior': None,
            'fuente_pga': 'SIN_DATOS'
        }

    periodo_anterior = periodos_anteriores['PERIODO'].max()
    row_anterior = estudiante_rendimiento_sorted[
        estudiante_rendimiento_sorted['PERIODO'] == periodo_anterior
    ].iloc[0]

    return {
        'codigo_estudiante': codigo_estudiante,
        'periodo': int(periodo_mas_reciente),
        'pga_anterior': float(row_anterior['PGA']) if pd.notna(row_anterior['PGA']) else None,
        'semestres_anteriores': int(row_anterior['TOTAL_SEMESTRES_MATRICULADOS']) if pd.notna(row_anterior['TOTAL_SEMESTRES_MATRICULADOS']) else None,
        'pct_creditos_anterior': float(row_anterior['PORCENTAJE_CREDITOS_APROBADOS']) if pd.notna(row_anterior['PORCENTAJE_CREDITOS_APROBADOS']) else None,
        'fuente_pga': 'PGA_HISTORICO',
        'periodo_fuente': int(periodo_anterior)
    }
