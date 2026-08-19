import type { SchedulePayload, Section } from '../types';
import {
  WEEK_DAYS,
  TIMELINE_PADDING,
  getTimelineConfig,
  expandMeetings,
  parseClockToMinutes,
  sectionKey,
  formatTimeRange,
} from '../utils/schedule';
import { courseColor } from '../utils/courseColor';

interface Props {
  payload: SchedulePayload;
  hoveredSection: Section | null;
  hoveredSectionKey: string | null;
  activeSectionKey: string | null;
  conflictMap: Map<string, Section[]>;
  onHoverSection: (key: string | null) => void;
  onSetActive: (key: string) => void;
}

const LINE = '#f1ece2';

export default function TimetableView({
  payload,
  hoveredSection,
  hoveredSectionKey,
  activeSectionKey,
  conflictMap,
  onHoverSection,
  onSetActive,
}: Props) {
  const items = expandMeetings(payload.items || []);
  const timedItems = items.filter((item) => item.days?.length && item.start_time && item.end_time);
  const timeline = getTimelineConfig(items);

  const visibleDays = WEEK_DAYS.filter((day) => {
    if (day !== 'Sat' && day !== 'Sun') return true;
    return timedItems.some((item) => item.days.includes(day));
  });

  if (!timedItems.length) {
    return (
      <div className="timetable">
        <div className="tt-fallback">
          No timed sections yet.
          <br />
          Search and add a course to build your week.
        </div>
      </div>
    );
  }

  const laneHeight = timeline.height + TIMELINE_PADDING * 2;
  const gridColumns = `52px repeat(${visibleDays.length}, minmax(0, 1fr))`;

  function blockStyle(section: Section): React.CSSProperties {
    const start = parseClockToMinutes(section.start_time);
    const end = parseClockToMinutes(section.end_time);
    const top =
      TIMELINE_PADDING +
      ((start - timeline.startHour * 60) / timeline.totalMinutes) * timeline.height;
    const height = Math.max(((end - start) / timeline.totalMinutes) * timeline.height, 40);
    return { top: `${top}px`, height: `${height - 3}px` };
  }

  const columnBackground: React.CSSProperties = {
    backgroundImage: `repeating-linear-gradient(to bottom, transparent 0, transparent 59px, ${LINE} 59px, ${LINE} 60px)`,
    backgroundPosition: `0 ${TIMELINE_PADDING}px`,
  };

  const isHoveredAlreadyPlaced =
    hoveredSection && items.some((s) => sectionKey(s) === sectionKey(hoveredSection));

  return (
    <div className="timetable">
      <div className="timetable-head" style={{ gridTemplateColumns: gridColumns }}>
        <div />
        {visibleDays.map((day) => (
          <div key={day} className="timetable-day">
            <div className="timetable-day-short">{day}</div>
          </div>
        ))}
      </div>

      <div className="timetable-grid">
        <div
          className="timetable-canvas"
          style={{ gridTemplateColumns: gridColumns, height: `${laneHeight}px` }}
        >
          <div className="timetable-gutter">
            {timeline.hours.map((hour) => {
              const top =
                TIMELINE_PADDING +
                ((hour - timeline.startHour) / (timeline.endHour - timeline.startHour)) *
                  timeline.height;
              const meridiem = hour >= 12 ? 'PM' : 'AM';
              let display = hour % 12;
              if (display === 0) display = 12;
              return (
                <div key={hour} className="timetable-hour" style={{ top: `${top}px` }}>
                  {display} {meridiem}
                </div>
              );
            })}
          </div>

          {visibleDays.map((day) => {
            const dayItems = timedItems.filter((item) => item.days.includes(day));
            const showPreview =
              hoveredSection &&
              !isHoveredAlreadyPlaced &&
              hoveredSection.start_time &&
              hoveredSection.end_time &&
              hoveredSection.days?.includes(day);

            return (
              <div key={day} className="timetable-col" style={columnBackground} data-day={day}>
                {dayItems.length === 0 && <div className="tt-empty">·</div>}

                {showPreview && hoveredSection && (
                  <div
                    className="tt-ghost"
                    style={{
                      ...blockStyle(hoveredSection),
                      background: `${courseColor(hoveredSection.course_code).bg}cc`,
                      border: `1.5px dashed ${courseColor(hoveredSection.course_code).color}`,
                      color: courseColor(hoveredSection.course_code).color,
                    }}
                  >
                    <span className="tt-ghost-code">{hoveredSection.course_code}</span>
                  </div>
                )}

                {dayItems.map((item) => {
                  const key = sectionKey(item);
                  const { color, bg } = courseColor(item.course_code);
                  const conflicted = conflictMap.has(`${key}::${day}`);
                  return (
                    <div
                      key={key}
                      className={`tt-block${hoveredSectionKey === key ? ' is-hovered' : ''}${
                        activeSectionKey === key ? ' is-active' : ''
                      }${conflicted ? ' is-conflict' : ''}`}
                      data-section-key={key}
                      style={{
                        ...blockStyle(item),
                        background: bg,
                        borderColor: conflicted ? '#dc2626' : `${color}40`,
                        borderLeft: `3px solid ${color}`,
                      }}
                      onMouseEnter={() => onHoverSection(key)}
                      onMouseLeave={() => onHoverSection(null)}
                      onClick={() => onSetActive(key)}
                    >
                      {conflicted && <span className="tt-conflict-badge">!</span>}
                      <span className="tt-block-code" style={{ color }}>
                        {item.course_code}
                      </span>
                      <span className="tt-block-meta">
                        {item.class_title ? `${item.class_title} · ` : ''}
                        {formatTimeRange(item.start_time, item.end_time)}
                      </span>
                      <span className="tt-block-room">#{item.class_id}</span>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
