'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Form,
  InputGroup,
  ListGroup,
  Row,
  Spinner,
} from 'react-bootstrap';

import { getStudent, previewDifficulty } from '@/lib/api';
import { DifficultyCourse, DifficultyPreviewResponse } from '@/lib/types';

interface CourseWithCredits {
  code: string;
  credits: number;
}

function formatDifficultyLabel(rate: number) {
  if (rate < 0.75) {
    return { title: 'Alta dificultad', text: 'Tiene una tasa histórica de aprobación baja.' };
  }
  if (rate < 0.9) {
    return { title: 'Dificultad media', text: 'Tiene una exigencia intermedia.' };
  }
  return { title: 'Baja dificultad', text: 'Tiene una tasa histórica de aprobación alta.' };
}

function formatLoadVariation(std: number) {
  if (std < 0.08) {
    return { title: 'Carga pareja', text: 'Los cursos tienen una exigencia parecida entre sí.' };
  }
  if (std < 0.18) {
    return { title: 'Carga mixta', text: 'Hay una mezcla moderada de cursos más suaves y más exigentes.' };
  }
  return { title: 'Carga dispareja', text: 'Hay diferencias fuertes de exigencia entre cursos.' };
}

function levelLabel(level: string) {
  switch (level) {
    case 'N3':
      return 'N3';
    case 'N2':
      return 'N2';
    case 'N1':
      return 'N1';
    default:
      return 'GLOBAL';
  }
}

export default function Home() {
  const router = useRouter();

  const [studentInput, setStudentInput] = useState('');
  const [courseInput, setCourseInput] = useState('');
  const [maxCreditsInput, setMaxCreditsInput] = useState('20');
  const [pgaAnterior, setPgaAnterior] = useState('');
  const [semestresAnteriores, setSemestresAnteriores] = useState('');
  const [pctCreditosAnterior, setPctCreditosAnterior] = useState('');

  const [studentSuggestions, setStudentSuggestions] = useState<string[]>([]);
  const [courseSuggestions, setCourseSuggestions] = useState<string[]>([]);
  const [showStudentDropdown, setShowStudentDropdown] = useState(false);
  const [showCourseDropdown, setShowCourseDropdown] = useState(false);

  const [confirmedStudent, setConfirmedStudent] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<number | null>(null);
  const [selectedCourses, setSelectedCourses] = useState<CourseWithCredits[]>([]);
  const [maxCredits, setMaxCredits] = useState<number | null>(20);
  const [preview, setPreview] = useState<DifficultyPreviewResponse | null>(null);

  const [loadingStudent, setLoadingStudent] = useState(false);
  const [loadingCourse, setLoadingCourse] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [msg, setMsg] = useState<{ type: 'danger' | 'success' | 'warning'; text: string } | null>(null);
  const [previewError, setPreviewError] = useState('');

  const studentDropdownRef = useRef<HTMLDivElement>(null);
  const courseDropdownRef = useRef<HTMLDivElement>(null);
  const previewRequestIdRef = useRef(0);

  const totalCredits = useMemo(
    () => selectedCourses.reduce((sum, course) => sum + course.credits, 0),
    [selectedCourses],
  );

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (studentDropdownRef.current && !studentDropdownRef.current.contains(event.target as Node)) {
        setShowStudentDropdown(false);
      }
      if (courseDropdownRef.current && !courseDropdownRef.current.contains(event.target as Node)) {
        setShowCourseDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const searchStudents = async () => {
      if (studentInput.length < 3) {
        setStudentSuggestions([]);
        setShowStudentDropdown(false);
        return;
      }

      const res = await fetch(`/api/search-id?type=student&query=${encodeURIComponent(studentInput)}&limit=10`);
      const data = await res.json();
      setStudentSuggestions(data.results || []);
      setShowStudentDropdown((data.results || []).length > 0);
    };

    const timer = setTimeout(searchStudents, 250);
    return () => clearTimeout(timer);
  }, [studentInput]);

  useEffect(() => {
    const searchCourses = async () => {
      if (courseInput.length < 3) {
        setCourseSuggestions([]);
        setShowCourseDropdown(false);
        return;
      }

      const res = await fetch(`/api/search-id?type=course&query=${encodeURIComponent(courseInput)}&limit=10`);
      const data = await res.json();
      setCourseSuggestions(data.results || []);
      setShowCourseDropdown((data.results || []).length > 0);
    };

    const timer = setTimeout(searchCourses, 250);
    return () => clearTimeout(timer);
  }, [courseInput]);

  useEffect(() => {
    if (!confirmedStudent || selectedCourses.length === 0) {
      setPreview(null);
      setPreviewError('');
      setLoadingPreview(false);
      return;
    }

    const requestId = ++previewRequestIdRef.current;
    let cancelled = false;

    const timer = setTimeout(async () => {
      if (cancelled) {
        return;
      }

      if (!confirmedStudent || selectedCourses.length === 0) {
        setPreview(null);
        setPreviewError('');
        return;
      }

      try {
        setLoadingPreview(true);
        setPreviewError('');
        const data = await previewDifficulty({
          estudiante_id: confirmedStudent,
          cursos: selectedCourses.map((course) => course.code),
          periodo: selectedPeriod ?? undefined,
        });
        if (cancelled || requestId !== previewRequestIdRef.current) {
          return;
        }
        setPreview(data);
      } catch (error) {
        if (cancelled || requestId !== previewRequestIdRef.current) {
          return;
        }
        setPreview(null);
        setPreviewError(error instanceof Error ? error.message : 'No se pudo calcular la dificultad.');
      } finally {
        if (!cancelled && requestId === previewRequestIdRef.current) {
          setLoadingPreview(false);
        }
      }
    }, 400);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [confirmedStudent, selectedCourses, selectedPeriod]);

  const validateId = async (type: 'student' | 'course', id: string) => {
    const res = await fetch(`/api/validate-id?type=${type}&id=${id}`);
    return res.json();
  };

  const handleSearchStudent = async (studentId?: string) => {
    const idToSearch = (studentId || studentInput).trim();
    if (!idToSearch) return;

    setLoadingStudent(true);
    setMsg(null);

    try {
      const { exists } = await validateId('student', idToSearch);
      if (!exists) {
        setMsg({ type: 'danger', text: `El estudiante ${idToSearch} no existe en la base de datos.` });
        return;
      }

      const data = await getStudent(idToSearch);
      if (data.error) {
        setMsg({ type: 'danger', text: data.error });
        return;
      }

      if (data.pga_anterior !== null && data.pga_anterior !== undefined) {
        setPgaAnterior(Number(data.pga_anterior).toFixed(2));
      }
      if (data.semestres_anteriores !== null && data.semestres_anteriores !== undefined) {
        setSemestresAnteriores(Number(data.semestres_anteriores).toFixed(0));
      }
      if (data.pct_creditos_anterior !== null && data.pct_creditos_anterior !== undefined) {
        setPctCreditosAnterior((Number(data.pct_creditos_anterior) * 100).toFixed(0));
      }
      if (data.periodo !== null && data.periodo !== undefined) {
        setSelectedPeriod(Number(data.periodo));
      } else {
        setSelectedPeriod(null);
      }

      setConfirmedStudent(idToSearch);
      setStudentInput('');
      setShowStudentDropdown(false);
      setMsg({ type: 'success', text: `Estudiante encontrado. Datos cargados desde ${data.fuente_pga ?? 'histórico'}.` });
    } catch (error) {
      setMsg({ type: 'danger', text: error instanceof Error ? error.message : 'No se pudo consultar el estudiante.' });
    } finally {
      setLoadingStudent(false);
    }
  };

  const handleSearchCourse = async (courseId?: string) => {
    const idToSearch = (courseId || courseInput).trim();
    if (!idToSearch) return;

    if (selectedCourses.some((course) => course.code === idToSearch)) {
      setMsg({ type: 'warning', text: 'Ese curso ya está agregado.' });
      return;
    }

    setLoadingCourse(true);
    setMsg(null);

    try {
      const result = await validateId('course', idToSearch);

      if (!result.exists) {
        setMsg({ type: 'danger', text: `El curso ${idToSearch} no existe.` });
        return;
      }

      if (!result.isSelectable) {
        setMsg({ type: 'danger', text: 'Ese curso fue excluido del predictor porque tiene 0 créditos.' });
        return;
      }

      const credits = Number(result.credits || 0);
      const creditLimit = maxCredits ?? 20;

      if (totalCredits + credits > creditLimit) {
        setMsg({
          type: 'danger',
          text: `No se puede agregar. Se excede el máximo de ${creditLimit} créditos.`,
        });
        return;
      }

      setSelectedCourses((prev) => [...prev, { code: idToSearch, credits }]);
      setCourseInput('');
      setShowCourseDropdown(false);
    } finally {
      setLoadingCourse(false);
    }
  };

  const removeCourse = (code: string) => {
    setSelectedCourses((prev) => prev.filter((course) => course.code !== code));
  };

  const handleSubmit = () => {
    if (!confirmedStudent || selectedCourses.length === 0) return;

    const payload = {
      estudiante_id: confirmedStudent,
      cursos: selectedCourses.map((course) => course.code),
      creditos: totalCredits,
      periodo: selectedPeriod ?? undefined,
      pga_anterior: parseFloat(pgaAnterior),
      semestres_anteriores: parseInt(semestresAnteriores, 10),
      pct_creditos_anterior: parseFloat(pctCreditosAnterior) / 100,
    };

    sessionStorage.setItem('predictionPayload', JSON.stringify(payload));
    router.push('/results');
  };

  const averageDifficulty = preview?.semester_aggregates.DIFF_MEAN_WEIGHTED ?? null;
  const minDifficulty = preview?.semester_aggregates.DIFF_MIN ?? null;
  const stdDifficulty = preview?.semester_aggregates.DIFF_STD ?? null;

  const averageLabel = averageDifficulty !== null ? formatDifficultyLabel(averageDifficulty) : null;
  const hardestLabel = minDifficulty !== null ? formatDifficultyLabel(minDifficulty) : null;
  const variationLabel = stdDifficulty !== null ? formatLoadVariation(stdDifficulty) : null;

  const hardestCourse = preview?.difficulty_courses.reduce<DifficultyCourse | null>((hardest, course) => {
    if (!hardest || course.difficulty_rate < hardest.difficulty_rate) {
      return course;
    }
    return hardest;
  }, null);

  return (
    <main className="container py-5" style={{ maxWidth: '960px' }}>
      <div className="mb-4 text-center">
        <h1 className="display-5 fw-bold text-primary">Predictor académico</h1>
        <p className="text-muted mb-0">Selecciona un estudiante, define su carga y revisa el impacto esperado de los cursos.</p>
      </div>

      {msg && (
        <Alert variant={msg.type} onClose={() => setMsg(null)} dismissible>
          {msg.text}
        </Alert>
      )}

      <Card className="shadow-sm mb-4">
        <Card.Body>
          <div className="mb-4" ref={studentDropdownRef} style={{ position: 'relative' }}>
            <Form.Label className="fw-bold">Selecciona estudiante</Form.Label>
            {!confirmedStudent ? (
              <>
                <InputGroup>
                  <Form.Control
                    placeholder="Ej: EST_00111783"
                    value={studentInput}
                    onChange={(e) => setStudentInput(e.target.value)}
                    autoComplete="off"
                    disabled={loadingStudent}
                  />
                  <Button onClick={() => handleSearchStudent()} disabled={loadingStudent}>
                    {loadingStudent ? <Spinner size="sm" animation="border" /> : 'Buscar'}
                  </Button>
                </InputGroup>
                {showStudentDropdown && studentSuggestions.length > 0 && (
                  <ListGroup style={{ position: 'absolute', zIndex: 10, width: '100%', maxHeight: '200px', overflowY: 'auto' }}>
                    {studentSuggestions.map((id) => (
                      <ListGroup.Item action key={id} onClick={() => handleSearchStudent(id)}>
                        {id}
                      </ListGroup.Item>
                    ))}
                  </ListGroup>
                )}
              </>
            ) : (
              <div className="d-flex justify-content-between align-items-center p-3 border rounded bg-light">
                <div>
                  <strong>Estudiante seleccionado:</strong> <Badge bg="success" className="ms-2">{confirmedStudent}</Badge>
                </div>
                <Button variant="outline-danger" size="sm" onClick={() => setConfirmedStudent(null)}>Cambiar</Button>
              </div>
            )}
          </div>

          <Row className="g-3 mb-4">
            <Col md={4}>
              <Form.Label className="fw-bold">PGA anterior</Form.Label>
              <Form.Control value={pgaAnterior} onChange={(e) => setPgaAnterior(e.target.value)} />
            </Col>
            <Col md={4}>
              <Form.Label className="fw-bold">Semestres anteriores</Form.Label>
              <Form.Control value={semestresAnteriores} onChange={(e) => setSemestresAnteriores(e.target.value)} />
            </Col>
            <Col md={4}>
              <Form.Label className="fw-bold">% de créditos aprobados</Form.Label>
              <InputGroup>
                <Form.Control value={pctCreditosAnterior} onChange={(e) => setPctCreditosAnterior(e.target.value)} />
                <InputGroup.Text>%</InputGroup.Text>
              </InputGroup>
            </Col>
          </Row>

          <div className="mb-4">
            <Form.Label className="fw-bold">Máximo de créditos</Form.Label>
            <Form.Control
              type="number"
              min={1}
              max={30}
              value={maxCreditsInput}
              onChange={(e) => {
                setMaxCreditsInput(e.target.value);
                const value = parseInt(e.target.value, 10);
                setMaxCredits(Number.isNaN(value) ? null : value);
              }}
            />
          </div>

          <div className="mb-3" ref={courseDropdownRef} style={{ position: 'relative' }}>
            <Form.Label className="fw-bold">Agrega cursos</Form.Label>
            <InputGroup>
              <Form.Control
                placeholder="Ej: CRS_00017889"
                value={courseInput}
                onChange={(e) => setCourseInput(e.target.value)}
                autoComplete="off"
                disabled={loadingCourse}
              />
              <Button variant="secondary" onClick={() => handleSearchCourse()} disabled={loadingCourse}>
                {loadingCourse ? <Spinner size="sm" animation="border" /> : 'Agregar'}
              </Button>
            </InputGroup>
            {showCourseDropdown && courseSuggestions.length > 0 && (
              <ListGroup style={{ position: 'absolute', zIndex: 10, width: '100%', maxHeight: '200px', overflowY: 'auto' }}>
                {courseSuggestions.map((id) => (
                  <ListGroup.Item action key={id} onClick={() => handleSearchCourse(id)}>
                    {id}
                  </ListGroup.Item>
                ))}
              </ListGroup>
            )}
          </div>

          <div className="p-3 border rounded bg-light">
            <div className="d-flex flex-wrap gap-2">
              {selectedCourses.length === 0 && (
                <span className="text-muted">Aún no has agregado cursos.</span>
              )}
              {selectedCourses.map((course) => (
                <Badge bg="success" key={course.code} className="p-2">
                  {course.code} ({course.credits} créditos)
                  <span className="ms-2" style={{ cursor: 'pointer' }} onClick={() => removeCourse(course.code)}>
                    ×
                  </span>
                </Badge>
              ))}
            </div>
            <div className="mt-3 text-end text-muted">
              {totalCredits} / {maxCredits ?? 20} créditos
            </div>
          </div>
        </Card.Body>
      </Card>

      <section className="mb-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h2 className="h4 mb-0">Vista previa de dificultad</h2>
          {loadingPreview && <Spinner animation="border" size="sm" />}
        </div>

        {previewError && <Alert variant="danger">{previewError}</Alert>}

        {!loadingPreview && !preview && !previewError && (
          <Alert variant="light">Agrega al menos un curso para ver cómo cambia la dificultad del semestre.</Alert>
        )}

        {preview && averageLabel && hardestLabel && variationLabel && (
          <>
            <Row className="g-3 mb-3">
              <Col md={4}>
                <Card className="h-100 shadow-sm">
                  <Card.Body>
                    <div className="text-muted small mb-2">Dificultad promedio del semestre</div>
                    <div className="h5">{averageLabel.title}</div>
                    <p className="mb-0 text-muted">{averageLabel.text}</p>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={4}>
                <Card className="h-100 shadow-sm">
                  <Card.Body>
                    <div className="text-muted small mb-2">Curso más exigente</div>
                    <div className="h5">{hardestCourse?.course_code ?? 'Sin dato'}</div>
                    {/* <div className="h3">{hardestLabel.title}</div> */}
                    <p className="mb-0 text-muted">
                      {hardestCourse
                        ? `Con una tasa histórica de aprobación de ${(hardestCourse.difficulty_rate * 100).toFixed(1)}%.`
                        : hardestLabel.text}
                    </p>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={4}>
                <Card className="h-100 shadow-sm">
                  <Card.Body>
                    <div className="text-muted small mb-2">Variedad de exigencia</div>
                    <div className="h5">{variationLabel.title}</div>
                    <p className="mb-0 text-muted">{variationLabel.text}</p>
                  </Card.Body>
                </Card>
              </Col>
            </Row>

            <Card className="shadow-sm">
              <Card.Body>
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
                      {preview.difficulty_courses.map((course) => (
                        <tr key={course.course_code}>
                          <td><code>{course.course_code}</code></td>
                          <td>{course.credits}</td>
                          <td>{(course.difficulty_rate * 100).toFixed(1)}%</td>
                          <td>{formatDifficultyLabel(course.difficulty_rate).title}</td>
                          <td>{levelLabel(course.source_level)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card.Body>
            </Card>
          </>
        )}
      </section>

      <div className="d-flex justify-content-end">
        <Button
          variant="primary"
          size="lg"
          onClick={handleSubmit}
          disabled={
            !confirmedStudent ||
            selectedCourses.length === 0 ||
            !pgaAnterior ||
            !semestresAnteriores ||
            !pctCreditosAnterior
          }
        >
          Ver predicción
        </Button>
      </div>
    </main>
  );
}
