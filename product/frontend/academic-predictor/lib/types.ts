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

export interface DifficultyCourse {
  course_code: string;
  credits: number;
  difficulty_rate: number;
  source_level: 'N3' | 'N2' | 'N1' | 'GLOBAL' | string;
  professor?: string | null;
}

export interface DifficultyPreviewRequest {
  estudiante_id: string;
  cursos: string[];
  periodo?: number;
}

export interface DifficultyPreviewResponse {
  estudiante_id: string;
  periodo: number;
  total_courses: number;
  total_credits: number;
  difficulty_courses: DifficultyCourse[];
  semester_aggregates: {
    DIFF_MEAN_WEIGHTED: number;
    DIFF_MIN: number;
    DIFF_STD: number;
  };
}

export interface PredictionRequest {
  estudiante_id: string;
  cursos: string[];
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
  feature_values: Record<string, number>;
  difficulty_courses: DifficultyCourse[];
  difficulty_sources: Record<string, string>;
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
