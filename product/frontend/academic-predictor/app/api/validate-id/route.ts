import { NextRequest, NextResponse } from 'next/server';
import { checkIdExists, getCourseCredits, isCourseSelectable } from '@/lib/data-store';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get('type') as 'student' | 'course';
  const id = searchParams.get('id');

  if (!type || !id) {
    return NextResponse.json({ error: 'Missing parameters' }, { status: 400 });
  }

  const exists = checkIdExists(type, id);
  
  if (type === 'course' && exists) {
    const credits = getCourseCredits(id);
    const isSelectable = isCourseSelectable(id);
    return NextResponse.json({
      exists,
      credits,
      isSelectable,
      reason: isSelectable ? undefined : 'zero_credits',
    });
  }

  return NextResponse.json({ exists });
}
