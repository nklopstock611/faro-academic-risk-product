# faro-academic-risk-product

Data product for student academic risk prediction.

This repository contains the application layer of the project: a FastAPI backend and a Next.js frontend to look up a student, simulate a course selection, compute historical course difficulty, and estimate semester-level academic risk.

The paper / experiments repository is here:

- https://github.com/SantiagoM99/faro-academic-risk

That repository contains the research code, experiments, and training pipeline. This repository contains the serving application.

## What this repository includes

- `product/backend`
  Prediction API and difficulty feature pipeline.
- `product/frontend/academic-predictor`
  Web UI for using the model.
- `product/backend/models/v2_model.pkl`
  Serialized model artifact used by the backend.
- `product/backend/data`
  Local dataset snapshot used by the backend to build features.

## Structure

```text
product/
  backend/
    main.py
    data/
    helpers/
    models/
      v2_model.pkl
      consultar_estudiante.py
      historial_rendimiento_academico_estudiante_anonymized.parquet
      informacion_actual_estudiante_anonymized.parquet
    routers/
    schemas/
    services/
    src/
  frontend/
    academic-predictor/
```

## Requirements

- Python 3.11 or 3.12
- Node.js 20.9+ or 22.x
- `npm`

## Data required by the backend

The backend reads parquet files from `product/backend/data`.

Expected files:

- `historial_materias_estudiante_anonymized.parquet`
- `historial_rendimiento_academico_estudiante_anonymized.parquet`
- `percentiles_academicos_estudiante_anonymized.parquet`
- `riesgos_historicos_estudiante_pregrado_anonymized.parquet`
- `oferta_academica_anonymized.parquet`
- `informacion_actual_estudiante_anonymized.parquet`
- `informacion_financiera_estudiante_anonymized.parquet`
- `horarios_curso_anonymized.parquet`
- `historial_estados_academicos_estudiante_anonymized.parquet`
- `cursos_dictados_profesores_anonymized.parquet`
- `historial_rendimiento_profesores_anonymized.parquet`

Minimum required files for the current `v2` backend:

- `historial_materias_estudiante_anonymized.parquet`
- `historial_rendimiento_academico_estudiante_anonymized.parquet`
- `oferta_academica_anonymized.parquet`
- `informacion_actual_estudiante_anonymized.parquet`
- `cursos_dictados_profesores_anonymized.parquet`

In addition, `consultar_estudiante.py` reads these two files from `product/backend/models`:

- `historial_rendimiento_academico_estudiante_anonymized.parquet`
- `informacion_actual_estudiante_anonymized.parquet`

If you are setting up this repository from scratch, make sure those two copies also exist in `product/backend/models`.

## Model artifact

The current backend expects the model artifact at:

- `product/backend/models/v2_model.pkl`

If that file does not exist, the service has a runtime training fallback, but that is not the recommended operational setup.

The intended setup is to serve a pre-exported artifact.

## How to generate `v2_model.pkl`

The artifact is generated from the paper repository:

- https://github.com/SantiagoM99/faro-academic-risk

From that repository, with data configured correctly, run:

```powershell
python experiments/v2_features/export_v2_model.py --output v2_model.pkl
```

If you generate it from the research repository and want to use it here, copy the resulting file to:

```text
product/backend/models/v2_model.pkl
```

## How to run the backend

From the root of this repository:

```powershell
cd product\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend URL:

```text
http://localhost:8000
```

Main endpoints:

- `GET /health`
- `GET /consultar_estudiante/{estudiante_id}`
- `POST /preview-difficulty`
- `POST /predecir`

Swagger docs:

```text
http://localhost:8000/docs
```

## How to run the frontend

In another terminal:

```powershell
cd product\frontend\academic-predictor
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

## Example test case

Risk case that should work with the current backend:

- Student: `EST_00111783`
- Courses:
  - `CRS_00017886`
  - `CRS_00012176`
  - `CRS_00009826`
- Total credits: `8`

- Student: `EST_00111783`
- Courses:
  - `CRS_00000004`
    - `f796236ab07e0d8f3caa63da7f20aed69a1507ef05464be21be0f808c13cd307`
- Total credits: `4`
