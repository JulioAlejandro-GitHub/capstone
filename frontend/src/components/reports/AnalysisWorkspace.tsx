import { createContext, useContext, useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';

// Análisis de Modelos: one report, sections ordered from answer to evidence.
export const analysisSections = [
  { id: 'resumen', label: 'Resumen', question: '¿Qué muestran estos resultados y con qué advertencias?' },
  { id: 'aprendizaje', label: 'Aprendizaje', question: '¿Cómo evolucionó el entrenamiento y qué checkpoint se eligió?' },
  { id: 'desempeno', label: 'Desempeño clínico', question: '¿Cómo clasifica cada modelo la población evaluada?' },
  { id: 'errores', label: 'Errores y consenso', question: '¿Dónde falla cada modelo y dónde se complementan?' },
  { id: 'explicabilidad', label: 'Explicabilidad', question: '¿Qué evidencia visual explica las predicciones?' },
  { id: 'representaciones', label: 'Representaciones', question: '¿Qué representaciones internas aprendió el modelo?' },
  { id: 'trazabilidad', label: 'Trazabilidad', question: '¿De dónde proviene cada dato y qué es comparable?' },
] as const;
export type AnalysisSection = typeof analysisSections[number]['id'];
export const defaultAnalysisSection: AnalysisSection = 'resumen';
export const isAnalysisSection = (value: string | null | undefined): value is AnalysisSection =>
  analysisSections.some(section => section.id === value);

const tabId = (section: AnalysisSection) => `scc-tab-${section}`;
const panelId = (section: AnalysisSection) => `scc-panel-${section}`;

export function AnalysisSectionNav({ section, onSelect, states = {} }: {
  section: AnalysisSection; onSelect: (section: AnalysisSection) => void; states?: Partial<Record<AnalysisSection, { state: string; label: string }>>;
}) {
  const move = (event: KeyboardEvent<HTMLButtonElement>) => {
    const index = analysisSections.findIndex(item => item.id === section);
    const next = event.key === 'ArrowRight' ? index + 1 : event.key === 'ArrowLeft' ? index - 1 : event.key === 'Home' ? 0 : event.key === 'End' ? analysisSections.length - 1 : null;
    if (next === null) return;
    event.preventDefault();
    const target = analysisSections[(next + analysisSections.length) % analysisSections.length].id;
    onSelect(target);
    document.getElementById(tabId(target))?.focus();
  };
  return <nav className="scc-section-nav" aria-label="Secciones del análisis"><div role="tablist" aria-label="Secciones del análisis">
    {analysisSections.map(item => <button key={item.id} id={tabId(item.id)} type="button" role="tab" className="scc-section-tab"
      aria-selected={item.id === section} aria-controls={panelId(item.id)} tabIndex={item.id === section ? 0 : -1}
      title={item.question} onKeyDown={move} onClick={() => onSelect(item.id)}>
      {item.label}{states[item.id] && <span className="scc-state-dot" data-state={states[item.id]!.state} title={states[item.id]!.label} aria-label={states[item.id]!.label} />}
    </button>)}
  </div></nav>;
}

// Panels mount on first visit and stay mounted, so returning to a section keeps its filters and cache.
export function useVisitedSections(section: AnalysisSection) {
  const [visited, setVisited] = useState<AnalysisSection[]>([section]);
  useEffect(() => { setVisited(old => old.includes(section) ? old : [...old, section]); }, [section]);
  return visited.includes(section) ? visited : [...visited, section];
}

export function AnalysisPanel({ id, section, visited, children }: { id: AnalysisSection; section: AnalysisSection; visited: AnalysisSection[]; children: ReactNode }) {
  if (!visited.includes(id)) return null;
  const meta = analysisSections.find(item => item.id === id)!;
  return <section role="tabpanel" id={panelId(id)} aria-labelledby={tabId(id)} hidden={id !== section} className="scc-section-panel">
    <header className="scc-section-header"><h2>{meta.label}</h2><p className="scc-meta">{meta.question}</p></header>
    {children}
  </section>;
}

type TraceEntry = { title: string; content: ReactNode };
const TraceabilityContext = createContext<((entry: TraceEntry, trigger: HTMLElement) => void) | null>(null);

export function TraceabilityProvider({ children }: { children: ReactNode }) {
  const [entry, setEntry] = useState<TraceEntry | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLElement | null>(null);
  useEffect(() => { if (entry && !dialog.current?.open) dialog.current?.showModal(); }, [entry]);
  const open = (next: TraceEntry, source: HTMLElement) => { trigger.current = source; setEntry(next); };
  return <TraceabilityContext.Provider value={open}>
    {children}
    <dialog ref={dialog} className="ds-report scc-trace-drawer" aria-labelledby="scc-trace-title" onClose={() => { setEntry(null); trigger.current?.focus(); }}>
      <header className="scc-trace-header"><div><span className="scc-meta">Trazabilidad</span><h2 id="scc-trace-title">{entry?.title}</h2></div>
        <button type="button" className="ds-button" onClick={() => dialog.current?.close()}>Cerrar</button></header>
      <div className="scc-trace-body">{entry?.content}</div>
    </dialog>
  </TraceabilityContext.Provider>;
}

// Without a provider (isolated renders), evidence stays inline in a closed disclosure.
export function EvidenceButton({ title, label = 'Evidencia', children }: { title: string; label?: string; children: ReactNode }) {
  const open = useContext(TraceabilityContext);
  if (!open) return <details><summary>{title}</summary>{children}</details>;
  return <button type="button" className="ds-button scc-evidence-button" data-size="compact" aria-haspopup="dialog"
    title={title} onClick={event => open({ title, content: children }, event.currentTarget)}>ⓘ {label}</button>;
}
