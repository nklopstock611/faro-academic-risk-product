from pydantic import BaseModel, ConfigDict, Field


class CourseSelectionInput(BaseModel):
    course_code: str
    login_docente: str | None = None


class HistoricalMatchSummary(BaseModel):
    match_scope: str
    requested_with_sections: bool
    matches_found: int
    avg_semester_credits: float | None = None
    avg_semester_gpa: float | None = None
    median_semester_gpa: float | None = None
    avg_approved_pct: float | None = None
    avg_cumulative_gpa: float | None = None
    approved_pct_distribution: list[dict[str, int | str]] = Field(default_factory=list)


class HistoricalCombinationSummary(BaseModel):
    section_match: HistoricalMatchSummary | None = None
    course_match: HistoricalMatchSummary


class DifficultyPreviewRequest(BaseModel):
    estudiante_id: str
    cursos: list[CourseSelectionInput | str] = Field(min_length=1)
    periodo: int | None = None


class DifficultyCourseResponse(BaseModel):
    course_code: str
    login_docente: str | None = None
    credits: float
    difficulty_rate: float
    source_level: str
    professor: str | None = None


class DifficultyPreviewResponse(BaseModel):
    estudiante_id: str
    periodo: int
    total_courses: int
    total_credits: float
    course_selection: list[CourseSelectionInput]
    difficulty_courses: list[DifficultyCourseResponse]
    semester_aggregates: dict[str, float]
    difficulty_level_legend: dict[str, str]
    historical_combination_summary: HistoricalCombinationSummary


class V2PredictionRequest(BaseModel):
    estudiante_id: str
    cursos: list[CourseSelectionInput | str] = Field(min_length=1)
    creditos: float | None = None
    periodo: int | None = None
    pga_anterior: float | None = None
    semestres_anteriores: int | None = None
    pct_creditos_anterior: float | None = None


class V2PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    estudiante_id: str
    periodo: int
    model_version: str
    score: float
    at_risk: bool
    threshold: float
    score_p10: float | None = None
    score_p90: float | None = None
    score_std: float | None = None
    score_iqr: float | None = None
    confidence_level: str | None = None
    neighbor_count: int | None = None
    feature_values: dict[str, float]
    course_selection: list[CourseSelectionInput]
    difficulty_courses: list[DifficultyCourseResponse]
    difficulty_sources: dict[str, str]
    difficulty_level_legend: dict[str, str]
    historical_combination_summary: HistoricalCombinationSummary
    summary: dict[str, str | float | int]
