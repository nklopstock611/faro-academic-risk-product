from pydantic import BaseModel, Field


class DifficultyPreviewRequest(BaseModel):
    estudiante_id: str
    cursos: list[str] = Field(min_length=1)
    periodo: int | None = None


class DifficultyCourseResponse(BaseModel):
    course_code: str
    credits: float
    difficulty_rate: float
    source_level: str
    professor: str | None = None


class DifficultyPreviewResponse(BaseModel):
    estudiante_id: str
    periodo: int
    total_courses: int
    total_credits: float
    difficulty_courses: list[DifficultyCourseResponse]
    semester_aggregates: dict[str, float]


class V2PredictionRequest(BaseModel):
    estudiante_id: str
    cursos: list[str] = Field(min_length=1)
    creditos: float | None = None
    periodo: int | None = None
    pga_anterior: float | None = None
    semestres_anteriores: int | None = None
    pct_creditos_anterior: float | None = None


class V2PredictionResponse(BaseModel):
    estudiante_id: str
    periodo: int
    model_version: str
    score: float
    at_risk: bool
    threshold: float
    feature_values: dict[str, float]
    difficulty_courses: list[DifficultyCourseResponse]
    difficulty_sources: dict[str, str]
    summary: dict[str, str | float | int]
