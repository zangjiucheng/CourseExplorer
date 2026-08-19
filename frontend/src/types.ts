export interface Meeting {
  raw_time: string;
  start_time: string | null;
  end_time: string | null;
  days: string[];
}

export interface Section {
  class_id: number;
  course_code: string;
  class_title: string;
  available_seat: number | null;
  raw_time: string;
  start_time: string | null;
  end_time: string | null;
  days: string[];
  /** Every meeting this class has. Absent on responses from an older API. */
  meetings?: Meeting[];
}

export interface CourseResult {
  course_code: string;
  title: string;
  credit: string;
  description: string;
  requirements: string;
  sections: Section[];
  section_count: number;
  timed_section_count: number;
}

export interface SchedulePayload {
  term: string;
  items: Section[];
  weekly: Record<string, Section[]>;
  locked_items?: Section[];
  resolved_items?: Section[];
  unresolved_courses?: { course_code: string; reason: string }[];
  auto_resolved_courses?: string[];
}

export interface Toast {
  id: number;
  message: string;
}
