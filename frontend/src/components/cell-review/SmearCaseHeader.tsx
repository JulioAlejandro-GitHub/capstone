import type { ReactNode } from 'react';

export type SmearCaseHeaderStep = {
  id: string;
  label: string;
  state: string;
};

export type SmearCaseHeaderProps = {
  subjectCode: string | null;
  sampleCode: string | null;
  analysisRunCode: string | null;
  status: string;
  steps: SmearCaseHeaderStep[];
  compact: boolean;
  actions: ReactNode;
};

const stepGlyph = (state: string) => (
  state === 'complete' ? '✓' : state === 'warning' ? '!' : state === 'failed' ? '×' : '•'
);

/**
 * Single case header shared by the process panel and the immersive detail
 * view. The caller resolves every value (step states, status label,
 * actions); this component only lays them out, in full or compact form.
 */
export function SmearCaseHeader({
  subjectCode,
  sampleCode,
  analysisRunCode,
  status,
  steps,
  compact,
  actions,
}: SmearCaseHeaderProps) {
  return (
    <header className="workflow-context-header" data-compact={compact ? 'true' : 'false'}>
      <div className="workflow-case-context">
        <p className="workflow-kicker">Análisis de frotis</p>
        <strong>{subjectCode ?? '—'}</strong>
        <span>
          {sampleCode ?? '—'}
          {analysisRunCode ? ` · ${analysisRunCode}` : ''} · {status}
        </span>
      </div>
      <nav className="workflow-stage-nav" aria-label="Etapas del análisis">
        {steps.map((step) => (
          <span
            key={step.id}
            className="workflow-stage-item"
            data-state={step.state}
            aria-current={step.state === 'active' ? 'step' : undefined}
          >
            <span aria-hidden="true">{stepGlyph(step.state)}</span>
            <span className="workflow-stage-label">{step.label}</span>
          </span>
        ))}
      </nav>
      <div className="workflow-header-actions">{actions}</div>
    </header>
  );
}
