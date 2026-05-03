import studentIds from '@/public/data/codigos_estudiantes.json';
import courseIds from '@/public/data/codigos_cursos.json';
import courseCredits from '@/public/data/codigos_cursos_creditos.json';

export function getCourseCredits(courseId: string): number | null {
  return courseCredits[courseId as keyof typeof courseCredits] || null;
}

export function isCourseSelectable(courseId: string): boolean {
  const credits = getCourseCredits(courseId);
  return credits !== null && credits > 0;
}

export function searchIds(type: 'student' | 'course', query: string, limit: number = 10): string[] {
  const data = type === 'student'
    ? studentIds
    : courseIds.filter((id: string) => isCourseSelectable(id));

  const filtered = data.filter((id: string) =>
    id.toLowerCase().includes(query.toLowerCase())
  );

  return filtered.slice(0, limit);
}

export function checkIdExists(type: 'student' | 'course', id: string): boolean {
  const data = type === 'student' ? studentIds : courseIds;
  return data.includes(id);
}
