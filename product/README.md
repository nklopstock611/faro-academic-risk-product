# Proyecto Final - Ciencia de datos aplicada
## Sistema de predicción de éxito académico

Este proyecto consta de dos componentes principales:
- **Backend**: API REST desarrollada con FastAPI que ejecuta el modelo de predicción
- **Frontend**: Aplicación web desarrollada con Next.js y React

---

## Requisitos Previos

- Python 3.8 o superior
- Node.js 18 o superior
- npm o yarn

---

## Configuración e Instalación

### 1. Backend (FastAPI)

#### 1.1 Navegar al directorio del backend
```bash
cd producto_final/backend
```

#### 1.2 Crear ambiente virtual de Python
```bash
# En Windows
python -m venv venv

# En macOS/Linux
python3 -m venv venv
```

#### 1.3 Activar el ambiente virtual
```bash
# En Windows
venv\Scripts\activate

# En macOS/Linux
source venv/bin/activate
```

#### 1.4 Instalar dependencias
```bash
pip install -r requirements.txt
```

#### 1.5 Verificar archivos requeridos
Asegúrate de que los siguientes archivos estén en la carpeta `models/`:
- `lada_modelo.pkl` - Modelo entrenado
- `historial_rendimiento_academico_estudiante_anonymized.parquet`
- `informacion_actual_estudiante_anonymized.parquet`

#### 1.6 Ejecutar el servidor
```bash
# Desde la carpeta backend/
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

El servidor estará disponible en: `http://localhost:8000`

Para verificar que funciona, visita: `http://localhost:8000/docs` (documentación automática de la API)

---

### 2. Frontend (Next.js)

#### 2.1 Navegar al directorio del frontend
```bash
cd producto_final/frontend/academic-predictor
```

#### 2.2 Instalar dependencias
```bash
npm install
# o si prefieres yarn
yarn install
```

#### 2.3 Ejecutar el servidor de desarrollo
```bash
npm run dev
# o
yarn dev
```

El frontend estará disponible en: `http://localhost:3000`

---

## Estructura del Proyecto

```
producto_final/
├── backend/
│   ├── main.py                          # Punto de entrada de la API
│   ├── requirements.txt                 # Dependencias de Python
│   ├── models/
│   │   ├── lada_modelo.pkl             # Modelo de predicción
│   │   ├── lada_funciones.py           # Funciones del modelo
│   │   ├── histogram_creation_polars.py # Generación de histogramas
│   │   ├── example_of_students.py      # Utilidades
│   │   ├── historial_rendimiento_academico_estudiante_anonymized.parquet
│   │   └── informacion_actual_estudiante_anonymized.parquet
│   └── course_processing/
│       ├── course_processing.py        # Procesamiento de cursos
│       └── curso_creditos.json         # Mapeo de cursos y créditos
└── frontend/
    └── academic-predictor/
        ├── app/
        │   ├── page.tsx                # Página principal
        │   ├── layout.tsx              # Layout de la app
        │   ├── globals.css             # Estilos globales
        │   ├── api/                    # API routes
        │   └── results/
        │       └── page.tsx            # Página de resultados
        ├── public/
        │   └── data/
        │       ├── codigos_estudiantes.json
        │       ├── codigos_cursos.json
        │       └── codigos_cursos_creditos.json
        └── package.json
```

---

## Endpoints de la API

### POST `/predecir`
Realiza una predicción de éxito académico para un estudiante.

**Request Body:**
```json
{
  "estudiante_id": "EST_00123456",
  "cursos": ["CURSO_001", "CURSO_002"],
  "creditos": 15
}
```

**Response:**
```json
{
  "nivel_usado": "Nivel_3",
  "razon": "mainstream",
  "probabilidad_exito": 0.95,
  "cluster_id": 42,
  "num_estudiantes_similares": 87,
  "confianza": "ALTA",
  "total_clusters": 100,
  "histogram_gpa": [0.1, 0.2, ...],
  "histogram_total_semesters": [0.15, 0.25, ...],
  "histogram_percentage_credits": [0.12, 0.18, ...],
  "gpa_range": {"min": 0.0, "max": 5.0},
  "semesters_range": {"min": 1, "max": 15},
  "credits_range": {"min": 0, "max": 100},
  "student_gpa": 3.8,
  "student_total_semesters": 6,
  "student_percentage_credits": 85.5
}
```

---

## Uso de la Aplicación

1. **Inicio**: En la página principal, ingresa el código de estudiante
2. **Selección de cursos**: Busca y selecciona los cursos que deseas analizar
3. **Resultados**: Visualiza:
   - Probabilidad de éxito académico
   - Detalles del clustering
   - Distribuciones del cluster (GPA, semestres, créditos)
   - Comparación con tu perfil actual (líneas punteadas en los gráficos)

---

## Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework web moderno para APIs
- **Pandas/Polars**: Procesamiento de datos
- **Scikit-learn**: Modelo de machine learning
- **Uvicorn**: Servidor ASGI

### Frontend
- **Next.js 15**: Framework de React
- **TypeScript**: Tipado estático
- **Bootstrap 5**: Componentes UI
- **D3.js**: Visualizaciones de datos
- **React Bootstrap**: Componentes React de Bootstrap

---

## Solución de Problemas

### Backend no inicia
- Verifica que el ambiente virtual esté activado
- Asegúrate de que todos los archivos `.parquet` estén en `models/`
- Verifica que el archivo `lada_modelo.pkl` exista

### Frontend no conecta con el Backend
- Confirma que el backend esté corriendo en `http://localhost:8000`
- Verifica la configuración de CORS en `main.py`
- Revisa la consola del navegador para errores

### Errores de dependencias
```bash
# Backend
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall

# Frontend
rm -rf node_modules package-lock.json
npm install
```

---

## Notas Importantes

- El backend debe estar corriendo antes de usar el frontend
- Los datos de estudiantes y cursos están anonimizados
- Las predicciones se basan en datos históricos
- La confianza del modelo depende del número de estudiantes similares encontrados

---
