import type { Section } from '../types';

const STORAGE_KEY = 'uw-course.plan.v1';

export interface StoredPlan {
  term: string;
  selections: { course_code: string; class_id: number }[];
}

/**
 * The plan is stored as course code + class id rather than whole sections.
 * Seats, times and titles all move between visits, so the stored ids only say
 * what to ask the server for; the sections themselves are re-fetched.
 */
export function loadStoredPlan(): StoredPlan | null {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null; // storage blocked: private window, or cookies turned off
  }
  if (!raw) return null;

  try {
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;

    const { term, selections } = parsed as Partial<StoredPlan>;
    if (typeof term !== 'string' || !term || !Array.isArray(selections)) return null;

    const clean = selections.filter(
      (item): item is StoredPlan['selections'][number] =>
        !!item && typeof item.course_code === 'string' && typeof item.class_id === 'number'
    );
    return { term, selections: clean };
  } catch {
    return null; // hand-edited, or written by a build that stored another shape
  }
}

export function saveStoredPlan(term: string, selections: Section[]): void {
  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        term,
        selections: selections.map((s) => ({ course_code: s.course_code, class_id: s.class_id })),
      })
    );
  } catch {
    // Over quota or blocked: the plan simply does not survive the reload.
  }
}
