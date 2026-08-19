export type PlanModalMode = 'import' | 'export';

interface Props {
  mode: PlanModalMode;
  text: string;
  onTextChange: (text: string) => void;
  onSubmit: () => void;
  onClose: () => void;
}

const COPY: Record<PlanModalMode, { title: string; desc: string; cta: string; placeholder?: string; readOnly?: boolean }> = {
  import: {
    title: 'Import plan text',
    desc: 'Paste a plan. A bare course code auto-resolves a section; add a class number to lock a specific one.',
    cta: 'Apply plan',
    placeholder: 'Class2026Spring\n\nCS 341\nMATH 239\nSTAT 230, 1234',
  },
  export: {
    title: 'Export plan text',
    desc: 'Copy this anywhere — paste it back later to restore your schedule.',
    cta: 'Copy to clipboard',
    readOnly: true,
  },
};

export default function PlanModal({ mode, text, onTextChange, onSubmit, onClose }: Props) {
  const copy = COPY[mode];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{copy.title}</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="modal-body">
          <p className="modal-desc">{copy.desc}</p>
          <textarea
            className="modal-textarea"
            spellCheck={false}
            placeholder={copy.placeholder}
            readOnly={copy.readOnly}
            value={text}
            onChange={(e) => onTextChange(e.target.value)}
          />
          <div className="modal-actions">
            <button type="button" className="modal-primary" onClick={onSubmit}>
              {copy.cta}
            </button>
            <button type="button" className="modal-cancel" onClick={onClose}>
              {mode === 'export' ? 'Done' : 'Cancel'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
