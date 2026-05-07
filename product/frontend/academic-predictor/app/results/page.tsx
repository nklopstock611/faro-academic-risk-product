'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Alert, Badge, Button, Card, Col, Row, Spinner } from 'react-bootstrap';

import { predict } from '@/lib/api';
import { HistoricalMatchSummary, PredictionResponse } from '@/lib/types';

function confidenceBadgeBg(level?: string | null): 'success' | 'warning' | 'danger' | 'secondary' {
  if (level === 'alta') return 'success';
  if (level === 'media') return 'warning';
  if (level === 'baja') return 'danger';
  return 'secondary';
}

function difficultyLabel(rate: number) {
  if (rate < 0.75) {
    return 'Alta dificultad';
  }
  if (rate < 0.9) {
    return 'Dificultad media';
  }
  return 'Baja dificultad';
}

function loadVariationLabel(std: number) {
  if (std < 0.08) {
    return 'Carga pareja';
  }
  if (std < 0.18) {
    return 'Carga mixta';
  }
  return 'Carga dispareja';
}

function formatPercent(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'Sin dato';
  }
  return `${(value * 100).toFixed(1)}%`;
}

function formatNumber(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'Sin dato';
  }
  return value.toFixed(2);
}

function supportTitle(summary: HistoricalMatchSummary | null | undefined) {
  if (!summary) {
    return 'Sin coincidencias';
  }
  return `${summary.matches_found} casos históricos`;
}

function HistoricalDistributionCard({
  title,
  summary,
}: {
  title: string;
  summary: HistoricalMatchSummary | null | undefined;
}) {
  const distribution = summary?.approved_pct_distribution ?? [];
  const maxCount = Math.max(1, ...distribution.map((bin) => bin.count));

  return (
    <Card className="h-100 shadow-sm">
      <Card.Body>
        <div className="text-muted small mb-2">{title}</div>
        <Row className="g-4 align-items-start">
          <Col md={5}>
            <div className="h4 mb-3">{supportTitle(summary)}</div>
            <div className="small text-muted mb-3">
              GPA semestral promedio: <strong>{formatNumber(summary?.avg_semester_gpa)}</strong>
            </div>
            <div className="small text-muted mb-3">
              Carga semestral promedio: <strong>{formatNumber(summary?.avg_semester_credits)} créditos</strong>
            </div>
            <div className="small text-muted mb-0">
              % promedio de créditos aprobados: <strong>{formatPercent(summary?.avg_approved_pct)}</strong>
            </div>
          </Col>
          <Col md={7}>
            <div className="small fw-semibold mb-2">Distribución de % de créditos aprobados</div>
            <div className="d-flex flex-column gap-2">
              {distribution.map((bin) => (
                <div key={bin.label} className="d-flex align-items-center gap-2">
                  <div style={{ width: '64px' }} className="small text-muted">{bin.label}</div>
                  <div className="flex-grow-1 bg-light rounded" style={{ height: '12px', overflow: 'hidden' }}>
                    <div
                      className="bg-primary h-100"
                      style={{ width: `${(bin.count / maxCount) * 100}%`, minWidth: bin.count > 0 ? '6px' : '0' }}
                    />
                  </div>
                  <div style={{ width: '28px' }} className="small text-end">{bin.count}</div>
                </div>
              ))}
            </div>
          </Col>
        </Row>
      </Card.Body>
    </Card>
  );
}

export default function ResultsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [result, setResult] = useState<PredictionResponse | null>(null);

  useEffect(() => {
    const runPrediction = async () => {
      const stored = sessionStorage.getItem('predictionPayload');
      if (!stored) {
        router.push('/');
        return;
      }

      try {
        const payload = JSON.parse(stored);
        const response = await predict(payload);
        setResult(response);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'No se pudo obtener la predicción.');
      } finally {
        setLoading(false);
      }
    };

    runPrediction();
  }, [router]);

  if (loading) {
    return (
      <div className="text-center mt-5">
        <Spinner animation="border" />
        <p className="mt-3">Calculando predicción...</p>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="container py-5">
        <Alert variant="danger">
          <Alert.Heading>No se pudo completar la predicción</Alert.Heading>
          <p className="mb-0">{error || 'No llegó respuesta del modelo.'}</p>
        </Alert>
        <Button variant="outline-secondary" onClick={() => router.push('/')}>
          Volver
        </Button>
      </div>
    );
  }

  const scorePercent = (result.score * 100).toFixed(1);
  const hasSectionMatches = (result.historical_combination_summary.section_match?.matches_found ?? 0) > 0;

  return (
    <main className="container py-5" style={{ maxWidth: '1040px' }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <Button variant="outline-secondary" onClick={() => router.push('/')}>
          {'<-'} Volver
        </Button>
        <Badge bg={result.at_risk ? 'danger' : 'success'} className="fs-6">
          {result.at_risk ? 'Riesgo' : 'Sin riesgo'}
        </Badge>
      </div>

      <Card className="shadow-sm mb-4 text-center">
        <Card.Body className="py-5">
          <div className="text-muted mb-2">Probabilidad estimada de éxito</div>
          <div className={`display-2 fw-bold ${result.at_risk ? 'text-danger' : 'text-success'}`}>
            {scorePercent}%
          </div>
          {result.score_p10 != null && result.score_p90 != null && (
            <div className="mt-3 d-flex justify-content-center align-items-center gap-2 flex-wrap">
              <span className="text-muted small">
                Rango plausible (p10–p90): <strong>{(result.score_p10 * 100).toFixed(0)}%–{(result.score_p90 * 100).toFixed(0)}%</strong>
              </span>
              {result.confidence_level && (
                <Badge bg={confidenceBadgeBg(result.confidence_level)}>
                  Confianza: {result.confidence_level}
                </Badge>
              )}
            </div>
          )}
          <p className="mt-3 mb-0 text-muted">{result.summary.message}</p>
        </Card.Body>
      </Card>

      <Row className="g-3 mb-4">
        <Col md={4}>
          <Card className="h-100 shadow-sm">
            <Card.Body>
              <div className="text-muted small mb-2">Dificultad promedio del semestre</div>
              <div className="h3">{difficultyLabel(result.summary.difficulty_mean_weighted)}</div>
              <p className="mb-0 text-muted">Una tasa histórica de aprobación más baja implica mayor exigencia.</p>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="h-100 shadow-sm">
            <Card.Body>
              <div className="text-muted small mb-2">Curso más exigente</div>
              <div className="h3">{result.summary.hardest_course}</div>
              <p className="mb-0 text-muted">
                Con una tasa histórica de aprobación de {(result.summary.hardest_course_difficulty * 100).toFixed(1)}%.
              </p>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="h-100 shadow-sm">
            <Card.Body>
              <div className="text-muted small mb-2">Variedad de exigencia</div>
              <div className="h3">{loadVariationLabel(result.summary.difficulty_std)}</div>
              <p className="mb-0 text-muted">Resume qué tan similares son entre sí los cursos seleccionados.</p>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="g-3 mb-4">
        <Col md={hasSectionMatches ? 6 : 12}>
          <HistoricalDistributionCard
            title={hasSectionMatches ? 'Histórico del curso (todas las secciones)' : 'Histórico del curso'}
            summary={result.historical_combination_summary.course_match}
          />
        </Col>
        {hasSectionMatches && (
          <Col md={6}>
            <HistoricalDistributionCard
              title="Histórico por login del docente"
              summary={result.historical_combination_summary.section_match}
            />
          </Col>
        )}
      </Row>
    </main>
  );
}
