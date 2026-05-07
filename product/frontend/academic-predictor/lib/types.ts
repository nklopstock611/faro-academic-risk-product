export interface StudentLookupResponse {
  codigo_estudiante?: string;
  periodo?: number | null;
  pga_anterior?: number | null;
  semestres_anteriores?: number | null;
  pct_creditos_anterior?: number | null;
  fuente_pga?: string;
  periodo_fuente?: number | null;
  error?: string;
}

export interface CourseSelection {
  course_code: string;
  login_docente?: string | null;
}

export interface DifficultyCourse {
  course_code: string;
  login_docente?: string | null;
  credits: number;
  difficulty_rate: number;
  source_level: 'N3' | 'N2' | 'N1' | 'GLOBAL' | string;
  professor?: string | null;
}

export interface HistoricalMatchSummary {
  match_scope: 'section' | 'course' | string;
  requested_with_sections: boolean;
  matches_found: number;
  avg_semester_credits?: number | null;
  avg_semester_gpa?: number | null;
  median_semester_gpa?: number | null;
  avg_approved_pct?: number | null;
  avg_cumulative_gpa?: number | null;
  approved_pct_distribution: Array<{
    label: string;
    count: number;
  }>;
}

export interface HistoricalCombinationSummary {
  section_match?: HistoricalMatchSummary | null;
  course_match: HistoricalMatchSummary;
}

export interface DifficultyPreviewRequest {
  estudiante_id: string;
  cursos: Array<CourseSelection | string>;
  periodo?: number;
}

export interface DifficultyPreviewResponse {
  estudiante_id: string;
  periodo: number;
  total_courses: number;
  total_credits: number;
  course_selection: CourseSelection[];
  difficulty_courses: DifficultyCourse[];
  semester_aggregates: {
    DIFF_MEAN_WEIGHTED: number;
    DIFF_MIN: number;
    DIFF_STD: number;
  };
  difficulty_level_legend: Record<string, string>;
  historical_combination_summary: HistoricalCombinationSummary;
}

export interface PredictionRequest {
  estudiante_id: string;
  cursos: Array<CourseSelection | string>;
  creditos?: number;
  periodo?: number;
  pga_anterior?: number;
  semestres_anteriores?: number;
  pct_creditos_anterior?: number;
}

export interface PredictionResponse {
  estudiante_id: string;
  periodo: number;
  model_version: string;
  score: number;
  at_risk: boolean;
  threshold: number;
  score_p10?: number | null;
  score_p90?: number | null;
  score_std?: number | null;
  score_iqr?: number | null;
  confidence_level?: 'alta' | 'media' | 'baja' | null;
  neighbor_count?: number | null;
  feature_values: Record<string, number>;
  course_selection: CourseSelection[];
  difficulty_courses: DifficultyCourse[];
  difficulty_sources: Record<string, string>;
  difficulty_level_legend: Record<string, string>;
  historical_combination_summary: HistoricalCombinationSummary;
  summary: {
    risk_label: string;
    message: string;
    total_courses: number;
    total_credits: number;
    hardest_course: string;
    hardest_course_difficulty: number;
    difficulty_mean_weighted: number;
    difficulty_min: number;
    difficulty_std: number;
  };
}
