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
  /** false only in mode 'setup': the fixed banner instead of the floating card. */
  compact: boolean;
  /**
   * Render the top-center stage band (compact mode only). False in 'review',
   * where the viewer's own toolbar occupies that band instead.
   */
  showStageBand?: boolean;
  actions?: ReactNode;
};

const stepGlyph = (state: string) => (
  state === 'complete' ? '✓' : state === 'warning' ? '!' : state === 'failed' ? '×' : '•'
);

const StepNav = ({ steps }: { steps: SmearCaseHeaderStep[] }) => (
  <nav className="workflow-stage-band workflow-stage-nav" aria-label="Etapas del análisis">
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
 * actions); this component only lays them out.
 *
 * compact=false renders the fixed banner used only in mode 'setup'.
 * compact=true renders a folded floating glass card, identical in
 * 'processing' and 'review'. Folded, it shows only a generic "Muestra"
 * heading; expanded, it shows every identity/fact field in one dense grid
 * (the .cell-detail-facts scale), never truncated. The stepper moves out of
 * the card entirely into the top-center stage band (showStageBand).
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
  showStageBand = false,
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

  const identityFacts: SmearCaseHeaderFact[] = [
    subjectCode ? { label: 'Paciente', value: subjectCode } : null,
    sampleCode ? { label: 'Muestra', value: sampleCode } : null,
    analysisRunCode ? { label: 'Run', value: analysisRunCode } : null,
    createdAt ? { label: 'Fecha', value: createdAt } : null,
  ].filter((fact): fact is SmearCaseHeaderFact => fact !== null);

  return (
    <>
      {showStageBand ? <StepNav steps={steps} /> : null}
      <section className="workflow-case-card" data-expanded={expanded ? 'true' : 'false'}>
        <header className="cell-panel-heading">
          <h2>Muestra</h2>
          {sampleCode ? <span className="workflow-case-card-code">{sampleCode}</span> : null}
          <button
            type="button"
            aria-expanded={expanded}
            aria-label={expanded ? 'Plegar datos de la muestra' : 'Expandir datos de la muestra'}
            onClick={() => setExpanded((current) => !current)}
          >
            {expanded ? '−' : '+'}
          </button>
        </header>
        {/*
          * One wrapper for everything the "+" reveals. It is `display: contents`
          * by default, so the floating card keeps the exact flow it always had;
          * inside the unified control bar it becomes a single absolute drawer
          * hanging under the "Muestra" group, so identity and "Volver al
          * historial" cannot land on two overlapping layers.
          */}
        <div className="workflow-case-card-drawer">
          {expanded ? (
            <div className="workflow-case-card-expanded">
              <dl className="cell-detail-facts">
                {[...identityFacts, ...facts].map((fact) => (
                  <div key={fact.label}><dt>{fact.label}</dt><dd>{fact.value}</dd></div>
                ))}
              </dl>
            </div>
          ) : null}
          {actions ? <div className="workflow-header-actions">{actions}</div> : null}
        </div>
      </section>
    </>
  );
}
