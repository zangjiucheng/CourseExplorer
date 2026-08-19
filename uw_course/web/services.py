from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from uw_course.DB.dbClass import dbClass


DAY_ALIASES = {
    "M": "Mon",
    "T": "Tue",
    "Tu": "Tue",
    "W": "Wed",
    "H": "Thu",
    "Th": "Thu",
    "F": "Fri",
    "S": "Sat",
    "Sa": "Sat",
    "U": "Sun",
    "Su": "Sun",
}

WEEK_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass(slots=True)
class ScheduleSelection:
    course_code: str
    class_id: int | None = None


def normalize_course_code(value: str) -> str:
    compact = re.sub(r"\s+", " ", value.strip().upper())
    match = re.match(r"^([A-Z]+)\s*(\d+[A-Z]?)$", compact)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return compact


def parse_days(raw_days: str) -> list[str]:
    cleaned = re.sub(r"[^A-Za-z]", "", raw_days or "")
    tokens = re.findall(r"Th|Tu|Sa|Su|[MTWHFSU]", cleaned)
    return [DAY_ALIASES[token] for token in tokens if token in DAY_ALIASES]


def parse_time_range(raw_value: str) -> tuple[str | None, str | None, list[str]]:
    if not raw_value:
        return None, None, []

    match = re.search(
        r"(?P<start>\d{1,2}:\d{2})\s*-\s*(?P<end>\d{1,2}:\d{2})\s*(?P<days>[A-Za-z]+)",
        raw_value,
    )
    if not match:
        return None, None, []

    start = _normalize_clock(match.group("start"))
    end = _normalize_clock(match.group("end"), start_hint=start)
    days = parse_days(match.group("days"))
    return start, end, days


def _normalize_clock(raw_clock: str, start_hint: str | None = None) -> str:
    hours_str, minutes_str = raw_clock.split(":")
    hours = int(hours_str)
    minutes = int(minutes_str)
    if start_hint is not None:
        start_hours = int(start_hint.split(":")[0])
        if hours < start_hours:
            hours += 12
    elif hours < 8:
        hours += 12
    return f"{hours:02d}:{minutes:02d}"


def time_to_minutes(raw_clock: str | None) -> int:
    if not raw_clock:
        return 0
    hours, minutes = raw_clock.split(":")
    return int(hours) * 60 + int(minutes)


class CourseService:
    def __init__(self, db: dbClass | None = None):
        self.db = db or dbClass()

    def list_terms(self) -> list[str]:
        return self.db.listClassCollections()

    def search_courses(self, term: str, query: str, limit: int = 24) -> list[dict]:
        normalized_query = normalize_course_code(query)
        if not normalized_query:
            return []

        self.db.switchCollection(term)
        query_regex = re.escape(normalized_query)
        docs = list(
            self.db.ClassSchedule.find(
                {
                    "$or": [
                        {"ClassIndex": {"$regex": query_regex, "$options": "i"}},
                        {"classTitle": {"$regex": query_regex, "$options": "i"}},
                    ]
                },
                {"_id": 1, "ClassIndex": 1, "classTitle": 1, "time": 1, "times": 1, "availableSeat": 1},
            ).limit(limit * 6)
        )

        grouped: dict[str, list[dict]] = defaultdict(list)
        for doc in docs:
            grouped[doc.get("ClassIndex", "")].append(doc)

        results = []
        for course_code in sorted(grouped):
            detail = self._get_course_detail(course_code) or {}
            sections = [self._serialize_section(doc) for doc in grouped[course_code]]
            timed_sections = [section for section in sections if section["days"] and section["start_time"]]
            results.append(
                {
                    "course_code": course_code,
                    "title": detail.get("courseTitle") or course_code,
                    "credit": detail.get("courseCredit") or "",
                    "description": detail.get("courseDescription") or "",
                    "requirements": detail.get("requirementsDescription") or "",
                    "sections": sections,
                    "section_count": len(sections),
                    "timed_section_count": len(timed_sections),
                }
            )
            if len(results) >= limit:
                break
        return results

    def get_course(self, term: str, course_code: str) -> dict:
        normalized_code = normalize_course_code(course_code)
        self.db.switchCollection(term)
        detail = self._get_course_detail(normalized_code) or {}
        docs = list(
            self.db.ClassSchedule.find(
                {"ClassIndex": normalized_code},
                {"_id": 1, "ClassIndex": 1, "classTitle": 1, "time": 1, "times": 1, "availableSeat": 1},
            )
        )
        return {
            "course_code": normalized_code,
            "description": detail.get("courseDescription") or "",
            "credit": detail.get("courseCredit") or "",
            "requirements": detail.get("requirementsDescription") or "",
            "sections": [self._serialize_section(doc) for doc in docs],
        }

    def build_schedule(self, term: str, selections: list[ScheduleSelection]) -> dict:
        self.db.switchCollection(term)
        schedule_items = []
        weekly: dict[str, list[dict]] = {day: [] for day in WEEK_DAYS}

        for selection in selections:
            filters = {"ClassIndex": normalize_course_code(selection.course_code)}
            if selection.class_id is not None:
                filters["_id"] = selection.class_id

            docs = list(
                self.db.ClassSchedule.find(
                    filters,
                    {"_id": 1, "ClassIndex": 1, "classTitle": 1, "time": 1, "times": 1, "availableSeat": 1},
                )
            )
            if not docs:
                continue

            for doc in docs:
                section = self._serialize_section(doc)
                schedule_items.append(section)
                for day in section["days"]:
                    weekly[day].append(section)

        for day in WEEK_DAYS:
            weekly[day].sort(key=lambda item: time_to_minutes(item["start_time"]))

        return {
            "term": term,
            "items": schedule_items,
            "weekly": weekly,
        }

    def resolve_plan(self, term: str, selections: list[ScheduleSelection]) -> dict:
        self.db.switchCollection(term)

        locked_items: list[dict] = []
        auto_courses: dict[str, list[dict]] = {}
        unresolved_courses: list[dict] = []
        seen_locked: set[tuple[str, int | None]] = set()
        seen_auto: set[str] = set()

        for selection in selections:
            course_code = normalize_course_code(selection.course_code)
            if not course_code:
                continue

            if selection.class_id is not None:
                key = (course_code, selection.class_id)
                if key in seen_locked:
                    continue
                seen_locked.add(key)
                docs = list(
                    self.db.ClassSchedule.find(
                        {"ClassIndex": course_code, "_id": selection.class_id},
                        {"_id": 1, "ClassIndex": 1, "classTitle": 1, "time": 1, "times": 1, "availableSeat": 1},
                    )
                )
                if not docs:
                    unresolved_courses.append(
                        {
                            "course_code": course_code,
                            "reason": f"Locked class #{selection.class_id} was not found.",
                        }
                    )
                    continue
                locked_items.append(self._serialize_section(docs[0]))
                continue

            if course_code in seen_auto:
                continue
            seen_auto.add(course_code)
            docs = list(
                self.db.ClassSchedule.find(
                    {"ClassIndex": course_code},
                    {"_id": 1, "ClassIndex": 1, "classTitle": 1, "time": 1, "times": 1, "availableSeat": 1},
                )
            )
            sections = [self._serialize_section(doc) for doc in docs]
            if not sections:
                unresolved_courses.append(
                    {
                        "course_code": course_code,
                        "reason": "No sections were found for this course.",
                    }
                )
                continue
            auto_courses[course_code] = self._prepare_candidate_sections(sections, locked_items)

        resolved_items = locked_items + self._resolve_best_sections(auto_courses, locked_items)
        schedule = self._build_schedule_payload(term, resolved_items)
        schedule["locked_items"] = locked_items
        schedule["resolved_items"] = resolved_items
        schedule["unresolved_courses"] = unresolved_courses
        schedule["auto_resolved_courses"] = sorted(auto_courses.keys())
        return schedule

    def parse_plan_text(self, raw_text: str) -> dict:
        lines = [line.split("#")[0].strip() for line in raw_text.splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            raise ValueError("Plan file is empty.")

        term = lines[0]
        selections = []
        for line in lines[1:]:
            course_part, _, class_part = line.partition(",")
            course_code = normalize_course_code(course_part)
            class_id = int(class_part.strip()) if class_part.strip() else None
            selections.append(
                {
                    "course_code": course_code,
                    "class_id": class_id,
                }
            )
        return {"term": term, "selections": selections}

    def export_plan_text(self, term: str, selections: list[ScheduleSelection]) -> str:
        lines = [term, ""]
        for selection in selections:
            if selection.class_id is None:
                lines.append(selection.course_code)
            else:
                lines.append(f"{selection.course_code}, {selection.class_id}")
        return "\n".join(lines) + "\n"

    def _serialize_section(self, doc: dict) -> dict:
        raw_time = doc.get("time") or ""
        start_time, end_time, days = parse_time_range(raw_time)
        # A class can meet more than once: a lab on alternating weeks, a second
        # weekly slot, a midterm with two sittings. "times" holds them all and
        # falls back to the single "time" for documents written before the
        # sync started recording them.
        raw_times = [value for value in (doc.get("times") or []) if value]
        if not raw_times and raw_time:
            raw_times = [raw_time]
        meetings = []
        for value in raw_times:
            meet_start, meet_end, meet_days = parse_time_range(value)
            meetings.append(
                {
                    "raw_time": value,
                    "start_time": meet_start,
                    "end_time": meet_end,
                    "days": meet_days,
                }
            )
        return {
            "class_id": doc.get("_id"),
            "course_code": doc.get("ClassIndex", ""),
            "class_title": (doc.get("classTitle") or "").strip(),
            "available_seat": doc.get("availableSeat"),
            "raw_time": raw_time,
            "start_time": start_time,
            "end_time": end_time,
            "days": days,
            "meetings": meetings,
        }

    @staticmethod
    def _section_meetings(section: dict) -> list[dict]:
        """The distinct weekly slots of a section, for the grid and for clashes.

        A biweekly lab lists one meeting per date, but a weekly timetable has
        nowhere to put the date: all of them land on the same day at the same
        hour. Collapsing them keeps one block per slot instead of stacking
        eleven identical ones. The full list stays on the section as
        "meetings" for anything that does care about the dates.
        """
        seen = set()
        slots = []
        for meeting in section.get("meetings") or []:
            if not (meeting.get("start_time") and meeting.get("end_time") and meeting.get("days")):
                continue
            key = (tuple(meeting["days"]), meeting["start_time"], meeting["end_time"])
            if key in seen:
                continue
            seen.add(key)
            slots.append(meeting)
        if slots:
            return slots
        if section.get("start_time") and section.get("end_time") and section.get("days"):
            return [section]
        return []

    def _build_schedule_payload(self, term: str, items: list[dict]) -> dict:
        weekly: dict[str, list[dict]] = {day: [] for day in WEEK_DAYS}
        for section in items:
            for meeting in self._section_meetings(section):
                entry = {**section, **{
                    "raw_time": meeting["raw_time"],
                    "start_time": meeting["start_time"],
                    "end_time": meeting["end_time"],
                    "days": meeting["days"],
                }} if meeting is not section else section
                for day in meeting["days"]:
                    weekly[day].append(entry)
        for day in WEEK_DAYS:
            weekly[day].sort(key=lambda item: time_to_minutes(item["start_time"]))
        return {
            "term": term,
            "items": items,
            "weekly": weekly,
        }

    def _prepare_candidate_sections(self, sections: list[dict], locked_items: list[dict]) -> list[dict]:
        prepared = []
        for section in sections:
            candidate = dict(section)
            candidate["_section_rank"] = self._section_type_rank(section["class_title"])
            candidate["_seat_rank"] = section["available_seat"] if isinstance(section["available_seat"], int) else -1
            candidate["_locked_conflicts"] = self._count_conflicts(section, locked_items)
            prepared.append(candidate)
        prepared.sort(
            key=lambda item: (
                item["_locked_conflicts"],
                item["_section_rank"],
                0 if item["start_time"] and item["end_time"] else 1,
                -item["_seat_rank"],
                item["class_id"] or 0,
            )
        )
        return prepared[:14]

    def _resolve_best_sections(self, auto_courses: dict[str, list[dict]], locked_items: list[dict]) -> list[dict]:
        course_codes = sorted(auto_courses, key=lambda code: (len(auto_courses[code]), code))
        best_score: tuple[int, int, int, int] | None = None
        best_selection: list[dict] = []

        def search(index: int, chosen: list[dict], conflicts: int, section_rank: int, untimed_count: int, seat_score: int) -> None:
            nonlocal best_score, best_selection

            if best_score is not None and conflicts > best_score[0]:
                return

            if index >= len(course_codes):
                score = (conflicts, section_rank, untimed_count, -seat_score)
                if best_score is None or score < best_score:
                    best_score = score
                    best_selection = chosen.copy()
                return

            code = course_codes[index]
            for candidate in auto_courses[code]:
                new_conflicts = conflicts + self._count_conflicts(candidate, locked_items) + self._count_conflicts(candidate, chosen)
                if best_score is not None and new_conflicts > best_score[0]:
                    continue
                chosen.append(candidate)
                search(
                    index + 1,
                    chosen,
                    new_conflicts,
                    section_rank + candidate["_section_rank"],
                    untimed_count + (0 if candidate["start_time"] and candidate["end_time"] else 1),
                    seat_score + max(candidate["_seat_rank"], 0),
                )
                chosen.pop()

        search(0, [], 0, 0, 0, 0)
        return [self._strip_solver_fields(item) for item in best_selection]

    def _strip_solver_fields(self, section: dict) -> dict:
        return {key: value for key, value in section.items() if not key.startswith("_")}

    def _count_conflicts(self, section: dict, others: list[dict]) -> int:
        # A class clashes if any of its meetings overlaps any of theirs, so a
        # second weekly slot cannot hide behind the first one.
        own = self._section_meetings(section)
        if not own:
            return 0

        count = 0
        for other in others:
            if section["course_code"] == other["course_code"] and section["class_id"] == other["class_id"]:
                continue
            if self._meetings_overlap(own, self._section_meetings(other)):
                count += 1
        return count

    @staticmethod
    def _meetings_overlap(first: list[dict], second: list[dict]) -> bool:
        for a in first:
            start_a = time_to_minutes(a["start_time"])
            end_a = time_to_minutes(a["end_time"])
            days_a = set(a["days"])
            for b in second:
                if not days_a.intersection(b["days"]):
                    continue
                if start_a < time_to_minutes(b["end_time"]) and time_to_minutes(b["start_time"]) < end_a:
                    return True
        return False

    def _section_type_rank(self, class_title: str) -> int:
        normalized = (class_title or "").strip().upper()
        if normalized.startswith("LEC"):
            return 0
        if normalized.startswith("SEM"):
            return 1
        if normalized.startswith("TST") or normalized.startswith("LAB") or normalized.startswith("TUT"):
            return 3
        if normalized.startswith("PRJ") or normalized.startswith("WRK") or normalized.startswith("CLN"):
            return 4
        if not normalized:
            return 5
        return 2

    def _get_course_detail(self, course_code: str) -> dict | None:
        if not course_code or " " not in course_code:
            return None
        faculty, course_num = course_code.split(" ", 1)
        return self.db.CourseDescribe.find_one(
            {"faculty": faculty, "courseIndex": course_num},
            {"_id": 0},
        )
