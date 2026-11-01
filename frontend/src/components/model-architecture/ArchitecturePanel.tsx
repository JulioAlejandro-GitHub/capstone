import { useState } from 'react';

import { useComparisonEvidence } from '../../hooks/useComparisonEvidence';
import { api } from '../../services/api';
import type { ModelArchitecture } from '../../types/modelArchitecture';
import type { ComparisonCache } from '../../utils/comparisonCache';
import { ArchitectureDetail } from './ArchitectureDetail';
import { resolveView } from './architectureViews';

const runLabel = (index: number) => `RUN ${String.fromCharCode(65 + index)}`;

/** Sección Arquitectura de Análisis de Modelos: one selected RUN at a time, read only while the section is open. */
export function ArchitecturePanel({ ids, labels, datasource, cache, active, selected, onSelect }: {
  ids: string[]; labels: (string | null | undefined)[]; datasource: string; cache: ComparisonCache; active: boolean;
  selected?: string | null; onSelect: (id: string) => void;
}) {
  const [revision, setRevision] = useState(0);
  const [requestedView, setRequestedView] = useState<string | null>(null);
  const [requestedPhase, setRequestedPhase] = useState<string | null>(null);
  const run = ids.find(id => id === selected) ?? ids[0];
  const key = run ? JSON.stringify(['architecture', datasource, run, revision]) : null;
  const { data, error, loading } = useComparisonEvidence<ModelArchitecture>(cache, key, () => api.getModelArchitecture(datasource, run), active);
  if (!run) return <p>Selecciona al menos un TRAIN para ver su arquitectura.</p>;
  const phases = data?.phases ?? [];
  const phase = phases.find(item => item.phase === requestedPhase)?.phase ?? phases.at(-1)?.phase ?? '';
  return <div className="mx-page">
    {ids.length > 1 && <div className="scc-segmented" role="group" aria-label="Modelo visible">{ids.map((id, index) => <button key={id} type="button" className="ds-button" data-size="compact"
      aria-pressed={id === run} onClick={() => onSelect(id)}>{runLabel(index)}{labels[index] ? ` · ${labels[index]}` : ''}</button>)}</div>}
    {loading && <p role="status">Consultando la arquitectura registrada…</p>}
    {error ? <div className="ds-callout" role="alert"><p>{error instanceof Error ? error.message : 'No fue posible cargar la arquitectura.'}</p>
      <button type="button" className="ds-button" onClick={() => { cache.clear(); setRevision(value => value + 1); }}>Reintentar</button></div> : null}
    {data?.state === 'missing' && <p className="ds-callout" data-tone="warning" role="status">{data.issues.join(' ')}</p>}
    {data?.state === 'available' && <ArchitectureDetail data={data} view={resolveView(data.family, requestedView)} phase={phase} datasource={datasource} explorerLink
      onView={setRequestedView} onPhase={setRequestedPhase} />}
  </div>;
}
