import type { CourseResult, SchedulePayload, Section } from './types';

async function requestJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || 'Request failed');
  return payload;
}

export const api = {
  getTerms: () =>
    requestJson<{ terms: string[] }>('/api/terms'),

  searchCourses: (term: string, q: string) =>
    requestJson<{ results: CourseResult[] }>(
      `/api/courses?term=${encodeURIComponent(term)}&q=${encodeURIComponent(q)}`
    ),

  getCourse: (term: string, code: string) =>
    requestJson<CourseResult & { sections: Section[] }>(
      `/api/courses/${encodeURIComponent(code)}?term=${encodeURIComponent(term)}`
    ),

  buildSchedule: (term: string, selections: { course_code: string; class_id: number }[]) =>
    requestJson<SchedulePayload>('/api/schedule', {
      method: 'POST',
      body: JSON.stringify({ term, selections }),
    }),

  parsePlan: (planText: string) =>
    requestJson<{ term: string; selections: { course_code: string; class_id: number | null }[] }>(
      '/api/plan/parse',
      { method: 'POST', body: JSON.stringify({ plan_text: planText }) }
    ),

  exportPlan: (term: string, selections: { course_code: string; class_id: number }[]) =>
    requestJson<{ plan_text: string }>('/api/plan/export', {
      method: 'POST',
      body: JSON.stringify({ term, selections }),
    }),

  resolvePlan: (term: string, selections: { course_code: string; class_id: number | null }[]) =>
    requestJson<SchedulePayload>('/api/plan/resolve', {
      method: 'POST',
      body: JSON.stringify({ term, selections }),
    }),
};
