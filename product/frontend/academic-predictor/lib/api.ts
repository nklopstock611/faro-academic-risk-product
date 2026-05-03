import {
  DifficultyPreviewRequest,
  DifficultyPreviewResponse,
  PredictionRequest,
  PredictionResponse,
  StudentLookupResponse,
} from '@/lib/types';

const API_BASE_URL = 'http://localhost:8000';

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || 'Request failed');
  }
  return response.json() as Promise<T>;
}

export async function getStudent(studentId: string): Promise<StudentLookupResponse> {
  const response = await fetch(`${API_BASE_URL}/consultar_estudiante/${studentId}`);
  return parseJson<StudentLookupResponse>(response);
}

export async function previewDifficulty(
  payload: DifficultyPreviewRequest,
): Promise<DifficultyPreviewResponse> {
  const response = await fetch(`${API_BASE_URL}/preview-difficulty`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return parseJson<DifficultyPreviewResponse>(response);
}

export async function predict(
  payload: PredictionRequest,
): Promise<PredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/predecir`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return parseJson<PredictionResponse>(response);
}
