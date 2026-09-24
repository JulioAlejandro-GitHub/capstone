import { useEffect, useState, type ReactNode } from 'react';

export type SmearCaseHeaderStep = {
  id: string;
  label: string;
  state: string;
};

export type SmearCaseHeaderFact = {
  label: string;
  value: string;
};

export type SmearCaseHeaderProps = {
  subjectCode: string | null;
  sampleCode: string | null;
  analysisRunCode: string | null;
  status: string;
  /** 'En vivo' | 'Histórico', already resolved by the caller. */
  modeLabel: string;
  /** Already formatted date/time string. Omitted (not '—') when unknown. */
  createdAt?: string | null;
  /** Lote/Dimensiones/Formato/Estado-style facts. Empty entries are skipped. */
  facts: SmearCaseHeaderFact[];
  steps: SmearCaseHeaderStep[];
  compact: boolean;
  actions?: ReactNode;
};

const stepGlyph = (state: string) => (
  state === 'complete' ? '✓' : state === 'warning' ? '!' : state === 'failed' ? '×' : '•'
);

const StepNav = ({ steps }: { steps: SmearCaseHeaderStep[] }) => (
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
);

const FactStrip = ({ facts }: { facts: SmearCaseHeaderFact[] }) => (
  facts.length ? (
    <dl className="workflow-header-facts">
      {facts.map((fact) => (
        <div key={fact.label}><dt>{fact.label}</dt><dd>{fact.value}</dd></div>
      ))}
    </dl>
  ) : null
);

/**
 * Single case header shared by the process panel and the immersive detail
 * view. The caller resolves every value (step states, status label, facts,
 * actions); this component only lays them out, in full or compact form.
 *
 * compact=false renders the fixed banner used while mode is 'processing'.
 * compact=true renders a folded floating glass card used while mode is
 * 'review'; expanding it reveals the same fact strip and stepper. The fold
 * choice is local UI state, reset to folded whenever compact turns on again.
 */
export function SmearCaseHeader({
  subjectCode,
  sampleCode,
  analysisRunCode,
  status,
  modeLabel,
  createdAt,
  facts,
  steps,
  compact,
  actions,
}: SmearCaseHeaderProps) {
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    if (!compact) setExpanded(false);
  }, [compact]);

  if (!compact) {
    return (
      <header className="workflow-context-header" data-compact="false">
        <div className="workflow-case-context">
          <p className="workflow-kicker">Análisis de frotis · {modeLabel}</p>
          <strong>{subjectCode ?? '—'}</strong>
          <span>
            {sampleCode ?? '—'}
            {analysisRunCode ? ` · ${analysisRunCode}` : ''} · {status}
          </span>
        </div>
        <FactStrip facts={facts} />
        <StepNav steps={steps} />
        {actions ? <div className="workflow-header-actions">{actions}</div> : null}
      </header>
    );
  }

  return (
    <section
      className="workflow-case-card smear-glass-panel"
      data-expanded={expanded ? 'true' : 'false'}
    >
      <button
        type="button"
        className="workflow-case-card-toggle"
        aria-expanded={expanded}
        onClick={() => setExpanded((current) => !current)}
      >
        <p className="workflow-kicker">Análisis de frotis · {modeLabel}</p>
        {analysisRunCode ? <strong className="workflow-case-card-code">{analysisRunCode}</strong> : null}
        <dl className="workflow-case-card-summary">
          {subjectCode ? <div><dt>Paciente</dt><dd>{subjectCode}</dd></div> : null}
          {sampleCode ? <div><dt>Muestra</dt><dd>{sampleCode}</dd></div> : null}
          {analysisRunCode ? <div><dt>Run</dt><dd>{analysisRunCode}</dd></div> : null}
        </dl>
        {createdAt ? <span className="workflow-case-card-date">{createdAt}</span> : null}
      </button>
      {expanded ? (
        <div className="workflow-case-card-expanded">
          <FactStrip facts={facts} />
          <StepNav steps={steps} />
        </div>
      ) : null}
      {actions ? <div className="workflow-header-actions">{actions}</div> : null}
    </section>
  );
}
