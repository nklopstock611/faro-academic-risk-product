'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Alert, Badge, Button, Card, Col, Row, Spinner } from 'react-bootstrap';

import { predict } from '@/lib/api';
import { PredictionResponse } from '@/lib/types';

function difficultyLabel(rate: number) {
  if (rate < 0.75) {
    return 'Alta dificultad';
  }
  if (rate < 0.9) {
    return 'Dificultad media';
  }
  return 'Baja dificultad';
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

  return (
    <main className="container py-5" style={{ maxWidth: '960px' }}>
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
              <p className="mb-0 text-muted">Es el curso con la menor tasa histórica de aprobación dentro de tu selección.</p>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="h-100 shadow-sm">
            <Card.Body>
              <div className="text-muted small mb-2">Variedad de exigencia</div>
              <div className="h3">
                {result.summary.difficulty_std < 0.08
                  ? 'Carga pareja'
                  : result.summary.difficulty_std < 0.18
                    ? 'Carga mixta'
                    : 'Carga dispareja'}
              </div>
              <p className="mb-0 text-muted">Resume qué tan similares son entre sí los cursos que piensas inscribir.</p>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/*
      <Card className="shadow-sm mb-4">
        <Card.Header className="bg-light fw-bold">Dificultad por curso</Card.Header>
        <Card.Body>
          <p className="text-muted mb-3">
            La dificultad se estima con la tasa histórica de aprobación del curso. Una tasa más baja implica un curso más exigente.
          </p>
          <div className="table-responsive">
            <table className="table align-middle mb-0">
              <thead>
                <tr>
                  <th>Curso</th>
                  <th>Créditos</th>
                  <th>Tasa</th>
                  <th>Lectura</th>
                  <th>Nivel</th>
                </tr>
              </thead>
              <tbody>
                {result.difficulty_courses.map((course) => (
                  <tr key={course.course_code}>
                    <td><code>{course.course_code}</code></td>
                    <td>{course.credits}</td>
                    <td>{(course.difficulty_rate * 100).toFixed(1)}%</td>
                    <td>{difficultyLabel(course.difficulty_rate)}</td>
                    <td>
                      <Badge bg={levelBadgeVariant(course.source_level)}>
                        {course.source_level}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card.Body>
      </Card>
      */}

      {/*
      <Card className="shadow-sm">
        <Card.Header className="bg-light fw-bold">Feature values</Card.Header>
        <Card.Body>
          <pre className="mb-0">{JSON.stringify(result.feature_values, null, 2)}</pre>
        </Card.Body>
      </Card>
      */}
    </main>
  );
}
