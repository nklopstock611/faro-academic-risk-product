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
  Modal,
  Row,
  Spinner,
} from 'react-bootstrap';

import { getStudent, previewDifficulty } from '@/lib/api';
import { CourseSelection, DifficultyPreviewResponse } from '@/lib/types';

interface CourseWithCredits extends CourseSelection {
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

function levelLabel(level: string) {
  switch (level) {
    case 'N3':
      return 'N3 (curso + login docente)';
    case 'N2':
      return 'N2 (curso)';
    case 'N1':
      return 'N1 (departamento)';
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
  const [showDifficultyHelp, setShowDifficultyHelp] = useState(false);

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

      try {
        setLoadingPreview(true);
        setPreviewError('');
        const data = await previewDifficulty({
          estudiante_id: confirmedStudent,
          cursos: selectedCourses.map((course) => ({
            course_code: course.course_code,
            login_docente: course.login_docente || undefined,
          })),
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

    if (selectedCourses.some((course) => course.course_code === idToSearch)) {
      setMsg({ type: 'warning', text: 'Ese curso ya esta agregado.' });
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

      setSelectedCourses((prev) => [...prev, { course_code: idToSearch, credits, login_docente: '' }]);
      setCourseInput('');
      setShowCourseDropdown(false);
    } finally {
      setLoadingCourse(false);
    }
  };

  const updateCourseLoginDocente = (courseCode: string, value: string) => {
    setSelectedCourses((prev) =>
      prev.map((course) =>
        course.course_code === courseCode
          ? { ...course, login_docente: value }
          : course,
      ),
    );
  };

  const removeCourse = (courseCode: string) => {
    setSelectedCourses((prev) => prev.filter((course) => course.course_code !== courseCode));
  };

  const handleSubmit = () => {
    if (!confirmedStudent || selectedCourses.length === 0) return;

    const payload = {
      estudiante_id: confirmedStudent,
      cursos: selectedCourses.map((course) => ({
        course_code: course.course_code,
        login_docente: course.login_docente?.trim() ? course.login_docente.trim() : undefined,
      })),
      creditos: totalCredits,
      periodo: selectedPeriod ?? undefined,
      pga_anterior: parseFloat(pgaAnterior),
      semestres_anteriores: parseInt(semestresAnteriores, 10),
      pct_creditos_anterior: parseFloat(pctCreditosAnterior) / 100,
    };

    sessionStorage.setItem('predictionPayload', JSON.stringify(payload));
    router.push('/results');
  };

  return (
    <main className="container py-5" style={{ maxWidth: '1040px' }}>
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
            {selectedCourses.length === 0 && (
              <span className="text-muted">Aun no has agregado cursos.</span>
            )}

            {selectedCourses.length > 0 && (
              <div className="d-flex flex-column gap-3">
                {selectedCourses.map((course) => (
                  <div key={course.course_code} className="border rounded p-3 bg-white">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <div className="d-flex gap-2 align-items-center flex-wrap">
                        <Badge bg="success">{course.course_code}</Badge>
                        <span className="text-muted">{course.credits} créditos</span>
                      </div>
                      <Button variant="outline-danger" size="sm" onClick={() => removeCourse(course.course_code)}>
                        Quitar
                      </Button>
                    </div>
                    <Form.Label className="small text-muted mb-1">Login del docente (opcional)</Form.Label>
                    <Form.Control
                      placeholder="Ej: jperez"
                      value={course.login_docente ?? ''}
                      onChange={(e) => updateCourseLoginDocente(course.course_code, e.target.value)}
                    />
                    <div className="small text-muted mt-1">
                      Si indicas el login del docente, la dificultad puede calcularse al nivel mas especifico (curso + profesor).
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-3 text-end text-muted">
              {totalCredits} / {maxCredits ?? 20} créditos
            </div>
          </div>
        </Card.Body>
      </Card>

      <section className="mb-4">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <div className="d-flex align-items-center gap-2">
            <h2 className="h4 mb-0">Vista previa de dificultad</h2>
            <Button variant="outline-secondary" size="sm" onClick={() => setShowDifficultyHelp(true)}>
              ?
            </Button>
          </div>
          {loadingPreview && <Spinner animation="border" size="sm" />}
        </div>

        {previewError && <Alert variant="danger">{previewError}</Alert>}

        {!loadingPreview && !preview && !previewError && (
          <Alert variant="light">Agrega al menos un curso para ver cómo cambia la dificultad del semestre.</Alert>
        )}

        {preview && (
          <>
            <Card className="shadow-sm mb-3">
              <Card.Body>
                <div className="table-responsive">
                  <table className="table align-middle mb-0">
                    <thead>
                      <tr>
                        <th>Curso</th>
                        <th>Login docente</th>
                        <th>Créditos</th>
                        <th>Tasa</th>
                        <th>Lectura</th>
                        <th>Nivel</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.difficulty_courses.map((course) => (
                        <tr key={`${course.course_code}-${course.login_docente ?? 'base'}`}>
                          <td><code>{course.course_code}</code></td>
                          <td>{course.login_docente || 'No especificado'}</td>
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

            <Card className="shadow-sm">
              <Card.Body>
                <div className="fw-bold mb-2">Qué significa cada nivel</div>
                <ul className="mb-0">
                  {Object.entries(preview.difficulty_level_legend).map(([level, description]) => (
                    <li key={level}>
                      <strong>{level}:</strong> {description}
                    </li>
                  ))}
                </ul>
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
          Ver prediccion
        </Button>
      </div>

      <Modal show={showDifficultyHelp} onHide={() => setShowDifficultyHelp(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Cómo se calcula la dificultad</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>
            La dificultad se estima con la tasa histórica de aprobación. Una tasa menor implica un curso más exigente.
          </p>
          <p>
            El sistema intenta usar primero la información más específica disponible: curso con login del docente,
            luego curso, después departamento y, si no hay soporte suficiente, el promedio global.
          </p>
          <p className="mb-0">
            Para el histórico de combinaciones, si indicas el login del docente se intentan encontrar coincidencias a
            ese nivel. Si no existen, se sigue mostrando el histórico por código de curso.
          </p>
        </Modal.Body>
      </Modal>
    </main>
  );
}
