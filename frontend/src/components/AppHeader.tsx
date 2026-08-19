import { useEffect, useRef, useState } from 'react';
import GooseMark from './GooseMark';

interface Props {
  terms: string[];
  term: string;
  onTermChange: (term: string) => void;
  view: 'timetable' | 'explorer';
  onSetView: (view: 'timetable' | 'explorer') => void;
  selectedCount: number;
  conflictCount: number;
  onAutoResolve: () => void;
  onPlanText: () => void;
  onGoose: () => void;
}

export default function AppHeader({
  terms,
  term,
  onTermChange,
  view,
  onSetView,
  selectedCount,
  conflictCount,
  onAutoResolve,
  onPlanText,
  onGoose,
}: Props) {
  const [termOpen, setTermOpen] = useState(false);
  const termRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!termOpen) return;
    function handleClick(event: MouseEvent) {
      if (termRef.current && !termRef.current.contains(event.target as Node)) {
        setTermOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [termOpen]);

  return (
    <header className="app-header">
      <div className="brand">
        <span className="brand-mark">
          <GooseMark size={20} tone="dark" />
        </span>
        <span className="brand-name">
          UW Course <span>Planner</span>
        </span>
      </div>

      <div className="term-select" ref={termRef}>
        <button
          type="button"
          className="term-select-btn"
          onClick={() => setTermOpen((open) => !open)}
        >
          <span className="term-select-dot" />
          {term || 'Select term'}
          <span className="term-select-caret">▾</span>
        </button>
        {termOpen && (
          <div className="term-menu">
            {terms.map((t) => (
              <button
                key={t}
                type="button"
                className={`term-menu-item${t === term ? ' is-active' : ''}`}
                onClick={() => {
                  onTermChange(t);
                  setTermOpen(false);
                }}
              >
                {t}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="header-spacer" />

      <div className="view-toggle">
        <button
          type="button"
          className={`view-tab${view === 'timetable' ? ' is-active' : ''}`}
          onClick={() => onSetView('timetable')}
        >
          Timetable
        </button>
        <button
          type="button"
          className={`view-tab${view === 'explorer' ? ' is-active' : ''}`}
          onClick={() => onSetView('explorer')}
        >
          Explorer
        </button>
      </div>

      <button
        type="button"
        className="header-btn"
        onClick={onAutoResolve}
        disabled={selectedCount === 0}
        title={
          selectedCount === 0
            ? 'Add courses to your plan first'
            : 'Re-pick the best non-conflicting sections for the courses in your plan'
        }
      >
        <span className="header-btn-glyph">⤳</span>Auto-resolve
      </button>
      <button type="button" className="header-btn" onClick={onPlanText}>
        Plan text
      </button>

      <div className="header-divider" />

      <div className={`header-stat${conflictCount > 0 ? ' is-conflict' : ''}`}>
        <strong>{selectedCount}</strong>
        <span>{conflictCount > 0 ? `sections · ${conflictCount} clash` : 'sections'}</span>
      </div>

      <button type="button" className="goose-btn" title="Release the goose" onClick={onGoose}>
        <GooseMark size={18} tone="light" />
      </button>
    </header>
  );
}
