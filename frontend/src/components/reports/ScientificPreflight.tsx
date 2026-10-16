import { ComparisonPython, configurationEvidence, configurationLabels, CopyText } from './ComparisonPython';
import { Fragment, useMemo, useRef, useState } from 'react';
import { useAuth } from '../../auth';
import { api, ApiError } from '../../services/api';
import { useComparisonEvidence } from '../../hooks/useComparisonEvidence';
import { createComparisonCache, type ComparisonCache } from '../../utils/comparisonCache';
import type { AssessmentChoice } from '../../types/api';
import type { Dimension, EffectiveSelection, Finding, JsonValue, PopulationMember, Module, Observation, PreflightResponse, RequestedSelection, Verdict } from '../../types/scientificPreflight';
import { TrainingAssessmentXAI } from './AssessmentXAI';

const dimensions: Record<Dimension, string> = { A1: 'Dataset', A2: 'Partición', A3: 'Muestras', A4: 'Configuración experimental', A5: 'Checkpoint', A6: 'Evaluación' };
const modules: Record<Module, string> = { curves: 'Curvas de aprendizaje', metrics: 'Métricas VAL/TEST', consensus: 'Consenso y desacuerdo', xai: 'XAI', embeddings: 'Embeddings', pca: 'PCA', umap: 'UMAP', cka: 'CKA' };
export function observationText(value: Observation): string {
  if (value.state === 'known') return jsonText(value.value);
  if (value.state === 'query_error') return `ERROR_DE_CONSULTA · ${value.error_ids.join(', ')}`;
  return `${value.state === 'not_checked' ? 'No verificado' : value.state === 'not_applicable' ? 'No disponible (no aplica)' : 'Sin evidencia'} · ${value.reason}`;
}
function jsonText(value: JsonValue): string {
  if (value === null) return 'Sin evidencia';
  if (typeof value === 'boolean') return value ? 'Sí' : 'No';
  if (typeof value !== 'object') return String(value);
  if (Array.isArray(value)) return value.length ? value.map(jsonText).join(', ') : 'No disponible';
  return Object.entries(value).map(([key, item]) => `${key}: ${jsonText(item)}`).join(' · ') || 'Sin evidencia';
}
function verdictText(value: Verdict) { return value.scientific_state ?? 'ERROR_DE_CONSULTA'; }
const stateLabels: Record<string, string> = { COMPARABLE: 'Comparable', COMPARABLE_CON_ADVERTENCIAS: 'Comparable con advertencias', NO_COMPARABLE: 'No comparable', EVIDENCIA_INSUFICIENTE: 'Evidencia insuficiente', ERROR_DE_CONSULTA: 'Error de consulta' };
function VerdictBadge({ verdict }: { verdict: Verdict }) { return <span className="scc-verdict" data-state={verdictText(verdict)}>{stateLabels[verdictText(verdict)]}</span>; }
export function groupWarnings(findings: Finding[]) {
  const groups = new Map<string, typeof findings>();
  for (const finding of findings) {
    const key = JSON.stringify([finding.code, finding.kind, finding.message, finding.condition]);
    groups.set(key, [...(groups.get(key) ?? []), finding]);
  }
  return [...groups.values()];
}
export function findingLabel(finding: Finding): string {
  if (finding.code === 'SPLIT_UNKNOWN') return 'Partición no acreditada';
  const field = finding.code.startsWith('CONFIGURATION_DIFFERENCE_') ? finding.code.slice('CONFIGURATION_DIFFERENCE_'.length).toLowerCase() : '';
  if (configurationLabels[field]) return `${configurationLabels[field]}: diferencia experimental`;
  if (finding.code === 'CONFIGURATION_INCOMPLETE') return 'Configuración experimental incompleta';
  return finding.message;
}
function ParameterDifference({ findings, field }: { findings: Finding[]; field: string }) {
  const differences = findings.filter(finding => finding.code === `CONFIGURATION_DIFFERENCE_${field.toUpperCase()}`);
  return differences.length ? <details><summary>Diferencia experimental</summary>{differences.map(finding => <p key={finding.reason_id}>{findingLabel(finding)} · {finding.message}<br /><code>{finding.code} · {finding.kind} · {finding.reason_id}</code></p>)}</details> : <span className="scc-meta">Sin diferencia informada</span>;
}
function CompactValue({ value }: { value: JsonValue | undefined }) {
  if (value === undefined || value === null) return <>Sin evidencia</>;
  if (typeof value === 'object' || (typeof value === 'string' && (value.length > 60 || /[0-9a-f]{8}-[0-9a-f]{4}-/i.test(value)))) return <details><summary>Ver valor completo</summary>{jsonText(value)}</details>;
  return <>{jsonText(value)}</>;
}

function architecture(data: PreflightResponse, selection: EffectiveSelection) {
  for (const ref of data.evidence) {
    if (ref.source !== 'A4' || !ref.selection_ids.includes(selection.selection_id) || ref.value.state !== 'known') continue;
    const value = ref.value.value;
    if (value && typeof value === 'object' && !Array.isArray(value) && typeof value.architecture === 'string') return value.architecture;
  }
  return 'Arquitectura sin evidencia';
}
function ErrorMessage({ error, retry }: { error: unknown; retry: () => void }) {
  const denied = error instanceof ApiError && (error.status === 401 || error.status === 403);
  return <div className="ds-callout" data-tone="rejected" role="alert"><p>{denied ? 'Error de autorización: no puedes consultar esta evidencia.' : 'ERROR_DE_CONSULTA: no se pudo recuperar la evidencia.'}</p><button className="ds-button" onClick={retry}>Reintentar</button></div>;
}

function EvaluationSelector({ id, cache, effective, onChange }: { id: string; cache: ComparisonCache; effective?: RequestedSelection; onChange: (selection: RequestedSelection) => void }) {
  const [requested, setRequested] = useState(false);
  const [revision, setRevision] = useState(0);
  const [attempt, setAttempt] = useState('');
  const [checkpoint, setCheckpoint] = useState('');
  const [split, setSplit] = useState<'' | 'train' | 'val' | 'test'>('');
  const choices = useComparisonEvidence(cache, requested ? JSON.stringify(['evaluations', id, revision]) : null, async () => {
    const all: AssessmentChoice[] = [];
    for (let offset = 0; ; offset += 100) {
      const page = await api.getTrainingAssessments(id, offset);
      if (page.items.some(item => item.training_run_id !== id)) throw new Error('Linaje incompatible');
      all.push(...page.items.filter(item => item.kind === 'evaluate'));
      if (page.items.length < 100) return all;
    }
  });
  const detail = useComparisonEvidence(cache, attempt ? JSON.stringify(['evaluation-detail', id, attempt, revision]) : null, async () => {
    const value = await api.getAssessment(attempt);
    if (value.id !== attempt || value.training_run_id !== id || value.kind !== 'evaluate') throw new Error('Identidad incompatible');
    return value;
  });
  return <section className="report-evidence" aria-label={`Selección de evidencia ${id}`}>
    <code className="report-identifier">{id}</code>
    <button className="ds-button" onClick={() => { setRequested(true); if (requested) setRevision(value => value + 1); }}>Consultar evaluaciones e intentos</button>
    {(choices.loading || detail.loading) && <p role="status">Cargando selección de evidencia…</p>}
    {(choices.error || detail.error) ? <ErrorMessage error={choices.error || detail.error} retry={() => setRevision(value => value + 1)} /> : null}
    {choices.data && <form onSubmit={event => {
      event.preventDefault();
      if (attempt && !detail.data) return;
      const selection: RequestedSelection = { training_run_id: id,
        ...(detail.data && attempt ? { evaluation: { source: 'assessment', identity_id: detail.data.identity_id, attempt_id: detail.data.id } as const } : {}),
        ...(split ? { split } : {}), ...(checkpoint ? { checkpoint_artifact_id: checkpoint } : {}) };
      onChange(selection);
    }}>
      <label>Evaluación / intento<select className="ds-control" value={attempt} onChange={event => setAttempt(event.target.value)}>
        <option value="">Sin evaluación seleccionada</option>
        {choices.data.map(item => <option key={item.attempt_id} value={item.attempt_id}>{item.split} · {item.state} · {item.attempt_id}</option>)}
      </select></label>
      {!choices.data.length && <p>Sin intentos EVALUATE disponibles.</p>}
      {detail.data && <p className="report-identifier">Identidad: {detail.data.identity_id} · Intento: {detail.data.id}<br />Split del intento: {detail.data.identity.split} · Checkpoint atribuido: {detail.data.identity.model.checkpoint_artifact_id ?? 'Sin evidencia'}</p>}
      <label>Split solicitado<select className="ds-control" value={split} onChange={event => setSplit(event.target.value as typeof split)}>
        <option value="">Según evidencia del intento</option><option value="train">TRAIN</option><option value="val">VAL</option><option value="test">TEST</option>
      </select></label>
      <label>Checkpoint solicitado (UUID opcional)<input className="ds-control" value={checkpoint} pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}" onChange={event => setCheckpoint(event.target.value)} /></label>
      <p>Sin UUID solicitado, el backend utiliza únicamente el checkpoint atribuido por la evidencia. No se elige el último intento.</p>
      <button className="ds-button" disabled={Boolean(attempt && !detail.data)}>Aplicar selección</button>
    </form>}
    <p className="report-identifier">Selección efectiva solicitada: {effective ? JSON.stringify(effective) : 'TRAIN sin evaluación explícita.'}</p>
  </section>;
}

function EvidenceCell({ data, selection, dimension }: { data: PreflightResponse; selection: EffectiveSelection; dimension: Dimension }) {
  const refs = data.evidence.filter(ref => ref.source === dimension && ref.selection_ids.includes(selection.selection_id));
  const selected = dimension === 'A1' ? selection.dataset_version_id : dimension === 'A2' ? selection.split : dimension === 'A5' ? selection.checkpoint : dimension === 'A6' ? selection.evaluation : null;
  return <>
    {selected && <p>{dimension === 'A1' ? 'dataset_version_id' : dimension === 'A2' ? 'Partición' : dimension === 'A5' ? 'Checkpoint seleccionado' : 'Identidad de evaluación'}: {observationText(selected)}</p>}
    {refs.map(ref => <div key={ref.evidence_id}><p>{observationText(ref.value)}</p><small>{ref.operation} · {ref.evidence_id} · {ref.verification === 'not_verified' ? 'No verificado' : 'Evidencia operacional'} · {ref.observed_at}</small></div>)}
    {!selected && !refs.length && <p>Sin evidencia</p>}
    {dimension === 'A2' && data.populations.map(population => <p key={population.population_id}>Identidad de población: {population.population_id} · Alineación: {observationText(population.alignment_key)} · {population.subset_rule ?? 'Sin regla de subconjunto acreditada'}</p>)}
    {dimension === 'A3' && data.populations.map(population => <div key={population.population_id}>
      <p>Intersección: {observationText(population.intersection_unique)} · Completa: {observationText(population.complete)}</p>
      {population.per_selection.filter(member => member.selection_id === selection.selection_id).map(member => <dl key={member.selection_id} className="ds-dl ds-dl--rows">
        {(['expected_unique', 'retrieved_rows', 'retrieved_unique', 'numerator', 'denominator', 'ratio', 'duplicate_count', 'label_conflict_count', 'missing_count', 'exclusive_count'] as const).map(field => <div key={field}><dt>{field}</dt><dd>{observationText(member[field])}</dd></div>)}
      </dl>)}
    </div>)}
    {dimension === 'A5' && <>
      {data.checkpoints.filter(check => check.selection_id === selection.selection_id).map(check => <div key={check.artifact_id}><p>Registro: {observationText(check.registered)} · Linaje: {observationText(check.lineage)}</p><p>Verificación física: No verificado · SHA-256: No verificado</p></div>)}
      <p>Época y política de selección: Sin evidencia en este contrato.</p>
    </>}
    {dimension === 'A6' && <p>{selection.selection_reason} · Split: {observationText(selection.split)} · Checkpoint: {observationText(selection.checkpoint)}</p>}
  </>;
}

const populationLabels = { expected_unique: 'Muestras esperadas', retrieved_rows: 'Filas recuperadas', retrieved_unique: 'Muestras únicas', intersection_unique: 'Intersección', complete: 'Cobertura completa', numerator: 'Numerador', denominator: 'Denominador', ratio: 'Cobertura', duplicate_count: 'Duplicados', label_conflict_count: 'Conflictos de etiqueta', missing_count: 'Muestras faltantes', exclusive_count: 'Muestras exclusivas' };
function CompactObservation({ value, technical = false }: { value?: Observation; technical?: boolean }) {
  if (!value) return <>Sin evidencia</>;
  if (value.state === 'known' && value.value === null) return <>Sin evidencia</>;
  if (value.state === 'known') return technical ? <details><summary>Identidad acreditada</summary><span className="report-identifier">{jsonText(value.value)}</span></details> : <CompactValue value={value.value} />;
  return <details><summary>{value.state === 'query_error' ? 'Error de consulta' : value.state === 'not_checked' ? 'No verificado' : value.state === 'not_applicable' ? 'No aplica' : 'Sin evidencia'}</summary>{observationText(value)}</details>;
}
function parameterRows(data: PreflightResponse, dimension: Dimension): { label: string; technical?: boolean; values: (Observation | undefined)[] }[] {
  const selected = (label: string, field: 'dataset_version_id' | 'split' | 'checkpoint' | 'evaluation', technical = false) => ({ label, technical, values: data.selections.map(selection => selection[field]) });
  if (dimension === 'A1') return [selected('Versión del dataset', 'dataset_version_id', true)];
  if (dimension === 'A2') return [selected('Partición', 'split')];
  if (dimension === 'A6') return [selected('Evaluación e intento', 'evaluation', true)];
  if (dimension === 'A5') return [selected('Checkpoint atribuido', 'checkpoint', true), ...(['registered', 'lineage'] as const).map(field => ({ label: field === 'registered' ? 'Registro de checkpoint' : 'Linaje', values: data.selections.map(selection => data.checkpoints.find(check => check.selection_id === selection.selection_id)?.[field]) }))];
  if (dimension === 'A3') return data.populations.flatMap((population, index) => Object.entries(populationLabels).map(([field, label]) => ({ label: `${data.populations.length > 1 ? `Población ${index + 1} · ` : ''}${label}`, values: data.selections.map(selection => field === 'intersection_unique' ? population.intersection_unique : field === 'complete' ? population.complete : population.per_selection.find(member => member.selection_id === selection.selection_id)?.[field as keyof typeof populationLabels & keyof PopulationMember]) })));
  return [];
}

export function PreflightEvidence({ data }: { data: PreflightResponse }) {
  return <>
    <div className="report-table-scroll" tabIndex={0} role="region" aria-label="Tabla A1–A6"><table className="report-data-table scc-preflight-table">
      <caption>¿Qué estamos comparando? Evidencia por TRAIN y alcance</caption>
      <thead><tr><th scope="col">Parámetro</th><th scope="col">Estado o diferencia</th>{data.selections.map((selection, index) => <th scope="col" key={selection.selection_id}>RUN {String.fromCharCode(65 + index)}<br /><small>{architecture(data, selection)}</small></th>)}</tr></thead>
      <tbody>{(Object.keys(dimensions) as Dimension[]).map(dimension => {
        const results = data.dimensions.filter(item => item.dimension === dimension);
        const fields = dimension === 'A4' ? Object.keys(configurationLabels).filter(key => data.evidence.some(ref => ref.source === 'A4' && ref.value.state === 'known' && ref.value.value && typeof ref.value.value === 'object' && !Array.isArray(ref.value.value) && key in ref.value.value)) : [];
        return <Fragment key={dimension}><tr className="scc-dimension-row"><th scope="row">{dimension} — {dimensions[dimension]}</th><td>{results.map(item => <div key={item.scope.scope_id}><VerdictBadge verdict={item.verdict} /><details><summary>Motivos y alcance</summary><code>{verdictText(item.verdict)}</code><p>{item.scope.question} · {item.scope.population}</p><p className="report-identifier">Participantes: {item.scope.participating_training_run_ids.join(', ')}</p>{item.findings.map(finding => <p key={finding.reason_id}>{finding.kind === 'difference' ? 'Diferencia experimental: ' : ''}{finding.message} · {finding.condition}<br /><code>{finding.code} · {finding.reason_id}</code><br />Referencias: {finding.evidence_ids.join(', ')}</p>)}{item.verdict.error_ids.length > 0 && <p>Errores: {item.verdict.error_ids.join(', ')}</p>}</details></div>)}</td>
        {data.selections.map(selection => <td key={selection.selection_id}>{dimension === 'A4' ? architecture(data, selection) : dimension === 'A2' ? <CompactValue value={selection.split.state === 'known' ? selection.split.value : undefined} /> : <span>Ver parámetros</span>}<details><summary>Detalles {dimension}</summary><code className="report-identifier">{selection.training_run_id}</code><CopyText text={selection.training_run_id} label="Copiar UUID" /><EvidenceCell data={data} selection={selection} dimension={dimension} /></details></td>)}</tr>
        {parameterRows(data, dimension).map((row, index) => <tr key={`parameter:${index}`}><th scope="row">{row.label}</th><td className="scc-meta">Estado por alcance arriba</td>{row.values.map((value, column) => <td key={data.selections[column].selection_id}><CompactObservation value={value} technical={row.technical} /></td>)}</tr>)}
        {fields.map(field => <tr key={field}>
          <th scope="row">{configurationLabels[field]}</th>
          <td><ParameterDifference findings={results.flatMap(item => item.findings)} field={field} /></td>
          {data.selections.map(selection => {
            const refs = configurationEvidence(data, selection.selection_id);
            return <td key={selection.selection_id}>{refs.length ? refs.map(ref => <div key={ref.evidence_id}>
              <CompactValue value={ref.value.state === 'known' && ref.value.value && typeof ref.value.value === 'object' && !Array.isArray(ref.value.value) ? ref.value.value[field] : undefined} />
            </div>) : 'Sin evidencia'}</td>;
          })}
        </tr>)}
        {dimension === 'A4' && <tr><td colSpan={data.selections.length + 2}><ComparisonPython data={data} /></td></tr>}
        </Fragment>;
      })}</tbody>
    </table></div>
    <h3>Estados por análisis</h3>
    {data.analyses.map(analysis => <details key={analysis.analysis_id} className="report-evidence"><summary>{modules[analysis.module_id]} · <VerdictBadge verdict={analysis.verdict} /></summary><code>{verdictText(analysis.verdict)}</code>
      <p>{analysis.scope.question} · Población: {analysis.scope.population}</p>
      <p className="report-identifier">Participantes: {analysis.scope.participating_training_run_ids.join(', ') || 'Sin evidencia'}</p>
      {analysis.findings.map(finding => <p key={finding.reason_id}>{finding.message}</p>)}
      {analysis.interpretation_limits.map(limit => <p key={limit}>{limit}</p>)}
      {analysis.individual_data.map(item => <p key={item.selection_id} className="report-identifier">{item.selection_id}: {observationText(item.availability)} · Referencias: {item.references.join(', ') || 'No disponible'}</p>)}
    </details>)}
  </>;
}

function ComparisonModules({ ids, datasource, selections, revision, onEvidenceChange }: { ids: string[]; datasource: string; selections: RequestedSelection[]; revision: number; onEvidenceChange: () => void }) {
  const [xaiVisited, setXaiVisited] = useState(false);
  const [scienceOpen, setScienceOpen] = useState(false);
  const [xaiOpen, setXaiOpen] = useState(false);
  return <>
    <details className="ds-accordion" open><summary>02 — Historia de aprendizaje</summary><p>Las curvas de aprendizaje se incorporarán en SCC-TRAIN.1</p></details>
    <details className="ds-accordion"><summary>03 — Datos comparables VAL/TEST</summary><p>Visualización de resultados pendiente de una etapa posterior.</p></details>
    <details className="ds-accordion" onToggle={event => setScienceOpen(event.currentTarget.open)}><summary>04 — Evidencia científica y explicabilidad</summary>
      <details className="ds-accordion" onToggle={event => { setXaiOpen(event.currentTarget.open); if (event.currentTarget.open) setXaiVisited(true); }}><summary>XAI — Evidencia por célula</summary>
        {xaiVisited && ids.map(id => <section key={id}><code className="report-identifier">{id}</code><TrainingAssessmentXAI key={JSON.stringify([datasource, selections.find(selection => selection.training_run_id === id), revision])} trainingRunId={id} datasource={datasource} active={scienceOpen && xaiOpen} onEvidenceChange={onEvidenceChange} /></section>)}
      </details>
      {['Embeddings / PCA / UMAP — Representación de células', 'CKA — Similitud de representaciones', 'Consenso y desacuerdo — Complementariedad de errores', 'Calibración y confianza', 'Falsos positivos', 'Evidencia discriminativa'].map(title => <details className="ds-accordion" key={title}><summary>{title}</summary><p>Módulo previsto. Resultados no implementados en esta etapa.</p></details>)}
    </details>
    <details className="ds-accordion"><summary>05 — Inspección de muestra unitaria</summary><p>Módulo previsto para una etapa posterior.</p></details>
  </>;
}

function ComparisonEvidenceSession({ ids, datasource, maximum }: { ids: string[]; datasource: string; maximum?: number }) {
  const cache = useMemo(createComparisonCache, []);
  const [overrides, setOverrides] = useState<Record<string, RequestedSelection>>({});
  const [revision, setRevision] = useState(0);
  const [xaiRevision, setXaiRevision] = useState(0);
  const [detailOpen, setDetailOpen] = useState(false);
  const detailRef = useRef<HTMLDetailsElement>(null);
  const selections = ids.map(id => overrides[id] ?? { training_run_id: id });
  const key = maximum !== undefined && ids.length >= 2 && ids.length <= maximum ? JSON.stringify(['preflight', datasource, selections, revision]) : null;
  const { data, error, loading } = useComparisonEvidence(cache, key, () => api.getComparisonPreflight(datasource, { selections }));
  const refresh = () => { cache.clear(); setRevision(value => value + 1); setXaiRevision(value => value + 1); };
  const findings = data ? [...new Map([...data.dimensions.flatMap(item => item.findings), ...data.analyses.flatMap(item => item.findings)].map(item => [item.reason_id, item])).values()] : [];
  return <>
    {ids.length > 0 && <details className="ds-accordion"><summary>Seleccionar evaluación, intento, split y checkpoint</summary>
      {ids.map(id => <EvaluationSelector key={`${id}:${revision}`} id={id} cache={cache} effective={overrides[id]} onChange={selection => setOverrides(previous => ({ ...previous, [id]: selection }))} />)}
    </details>}
    <section className="report-section" aria-label="Resumen metodológico" aria-busy={loading}>
      <div className="ds-page-header"><h2>Resumen metodológico</h2><button className="ds-button" onClick={refresh}>Actualizar evidencia</button></div>
      {!key && <p>Selecciona entre dos TRAIN y el máximo configurado para consultar el Preflight.</p>}
      {loading && <p role="status">Consultando Preflight…</p>}
      {error ? <ErrorMessage error={error} retry={refresh} /> : null}
      {data && <>
        <p>{data.selections.length} TRAIN participantes · {data.selections.map(selection => architecture(data, selection)).join(' / ')}</p>
        <div className="scc-analysis-grid">{data.analyses.map(analysis => <details key={analysis.analysis_id} className="scc-analysis"><summary><strong>{modules[analysis.module_id]}</strong><VerdictBadge verdict={analysis.verdict} /></summary><p>{analysis.scope.question}</p><code>{verdictText(analysis.verdict)}</code></details>)}</div>
        <p className="scc-meta">{data.evidence.length} referencias · Consulta: {data.generated_at}</p>
        <div className="scc-warnings">{groupWarnings(findings.filter(item => data.summary.warning_reason_ids.includes(item.reason_id))).map(group => {
          const affected = new Set(group.flatMap(item => item.affected_selection_ids));
          return <details key={group[0].reason_id} className="ds-callout" data-tone="warning"><summary>{findingLabel(group[0])} · {affected.size} RUN afectados</summary>{group.map(item => <div key={item.reason_id}><p>{item.message} · {item.condition}</p><code>{item.code} · {item.reason_id}</code><p>Participantes: {item.affected_selection_ids.map(id => { const index = data.selections.findIndex(selection => selection.selection_id === id); return index < 0 ? id : `RUN ${String.fromCharCode(65 + index)}`; }).join(', ')}</p><p className="report-identifier">Referencias: {item.evidence_ids.join(', ')}</p></div>)}</details>;
        })}</div>
        {data.consistency.limitations.map(limit => <p key={limit}>{limit}</p>)}
        {data.technical_errors.map(item => <p role="alert" key={item.error_id}>ERROR_DE_CONSULTA · {item.message} · {item.operation} · {item.error_id}</p>)}
      </>}
      <button className="ds-button" onClick={() => { setDetailOpen(true); detailRef.current?.querySelector('summary')?.focus(); }}>¿Qué estamos comparando?</button>
    </section>
    <details ref={detailRef} className="ds-accordion" open={detailOpen} onToggle={event => setDetailOpen(event.currentTarget.open)}><summary>01 — ¿Qué estamos comparando?</summary>
      {data ? <PreflightEvidence data={data} /> : <p>El detalle utiliza la misma consulta del resumen metodológico.</p>}
    </details>
    <ComparisonModules selections={selections} revision={xaiRevision} ids={ids} datasource={datasource} onEvidenceChange={() => { cache.clear(); setRevision(value => value + 1); }} />
  </>;
}

export function ScientificPreflight(props: { ids: string[]; datasource: string; maximum?: number }) {
  const { user, status } = useAuth();
  // Remount all retained evidence on a change of user, permissions, datasource or TRAIN set.
  const scope = JSON.stringify([user, status, props.datasource, props.ids]);
  return <Fragment key={scope}><ComparisonEvidenceSession {...props} /></Fragment>;
}
