import { NextRequest, NextResponse } from 'next/server';
import { searchIds } from '@/lib/data-store';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get('type') as 'student' | 'course';
  const query = searchParams.get('query') || '';
  const limit = parseInt(searchParams.get('limit') || '10');

  if (!type) {
    return NextResponse.json({ error: 'Missing type parameter' }, { status: 400 });
  }

  const results = searchIds(type, query, limit);
  
  return NextResponse.json({ results });
}