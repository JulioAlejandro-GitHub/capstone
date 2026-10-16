import { ScientificResults, ScientificQuestions, ScientificRepresentations, PersistedXAI } from './ScientificReport';
import { ComparisonPython, configurationEvidence, configurationLabels, CopyText } from './ComparisonPython';
import { Fragment, useMemo, useRef, useState } from 'react';
import { useAuth } from '../../auth';
import { api, ApiError } from '../../services/api';
import { useComparisonEvidence } from '../../hooks/useComparisonEvidence';
import { createComparisonCache, type ComparisonCache } from '../../utils/comparisonCache';
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
      <p>Época y política: consulte el módulo de curvas. El checksum registrado no acredita verificación física.</p>
    </>}
    {dimension === 'A6' && <p>{selection.selection_reason} · Split: {observationText(selection.split)} · Checkpoint: {observationText(selection.checkpoint)}</p>}
  </>;
}

const populationLabels = { expected_unique: 'Muestras esperadas', retrieved_rows: 'Filas recuperadas', retrieved_unique: 'Muestras únicas', intersection_unique: 'Intersección', complete: 'Cobertura completa', numerator: 'Numerador', denominator: 'Denominador', ratio: 'Cobertura', duplicate_count: 'Duplicados', label_conflict_count: 'Conflictos de etiqueta', missing_count: 'Muestras faltantes', exclusive_count: 'Muestras exclusivas' };
function parameterRows(data: PreflightResponse, dimension: Dimension): { label: string; technical?: boolean; values: (Observation | undefined)[] }[] {
  const selected = (label: string, field: 'dataset_version_id' | 'split' | 'checkpoint' | 'evaluation', technical = false) => ({ label, technical, values: data.selections.map(selection => selection[field]) });
  const projected = (source: Dimension, field: string, label: string) => ({label, values: data.selections.map(selection => {
    const ref = data.evidence.find(r => r.source === source && r.selection_ids.includes(selection.selection_id) && r.value.state === 'known' && r.value.value && typeof r.value.value === 'object' && !Array.isArray(r.value.value) && field in r.value.value);
    const object = ref?.value.state === 'known' ? ref.value.value : null;
    const value = object && typeof object === 'object' && !Array.isArray(object) ? object[field] : undefined;
    return value === undefined || value === null ? undefined : {state: 'known' as const, value, evidence_ids: ref ? [ref.evidence_id] : []};
  })});
  if (dimension === 'A1') return [selected('Versión del dataset', 'dataset_version_id', true), ...Object.entries({name:'Dataset',status:'Estado del dataset',grouping_strategy:'Estrategia',split_algorithm:'Algoritmo de split',random_seed:'Semilla de split',source_record_count:'Registros oficiales'}).map(([field,label]) => projected('A1',field,label))];
  if (dimension === 'A2') return [selected('Partición evaluada', 'split'), projected('A2','counts','Particiones oficiales'), projected('A2','checks','Controles de validación del split')];
  if (dimension === 'A6') return [selected('Evaluación e intento', 'evaluation', true), ...Object.entries({evaluation_role:'Tipo de evaluación',purpose:'Propósito',threshold:'Umbral',sample_count:'Muestras evaluadas',metric_definition:'Definición de métricas'}).map(([field,label]) => projected('A6',field,label))];
  if (dimension === 'A5') return [selected('Checkpoint atribuido', 'checkpoint', true), ...Object.entries({selected_epoch:'Época seleccionada',policy:'Política de selección',metric:'Métrica de selección',checksum_registered:'Checksum registrado (sin verificación física)'}).map(([field,label]) => ({...projected('A5',field,label), technical: field === 'checksum_registered'})), ...(['registered', 'lineage'] as const).map(field => ({ label: field === 'registered' ? 'Registro de checkpoint' : 'Linaje', values: data.selections.map(selection => data.checkpoints.find(check => check.selection_id === selection.selection_id)?.[field]) }))];
  if (dimension === 'A3') return [...Object.entries({materialization_status:'Estado de materialización',reconciliation_status:'Reconciliación',record_count:'Registros materializados',materialization_dataset_matches:'Materialización de la misma versión'}).map(([field,label]) => projected('A2',field,label)), ...data.populations.flatMap((population, index) => Object.entries(populationLabels).map(([field, label]) => ({ label: `${data.populations.length > 1 ? `Población ${index + 1} · ` : ''}${label}`, values: data.selections.map(selection => field === 'intersection_unique' ? population.intersection_unique : field === 'complete' ? population.complete : population.per_selection.find(member => member.selection_id === selection.selection_id)?.[field as keyof typeof populationLabels & keyof PopulationMember]) })))];
  return [];
}

export function PreflightEvidence({ data }: { data: PreflightResponse }) {
  const [expanded, setExpanded] = useState<string[]>([]);
  const [groups, setGroups] = useState(['Con diferencias', 'Comparables']);
  const rows = (Object.keys(dimensions) as Dimension[]).flatMap(dimension => {
    const results = data.dimensions.filter(item => item.dimension === dimension);
    const params = dimension === 'A4' ? Object.entries(configurationLabels).map(([field, label]) => ({label, technical: false,
      values: data.selections.map(selection => {
        const ref = configurationEvidence(data, selection.selection_id).find(r => r.value.state === 'known');
        const object = ref?.value.state === 'known' ? ref.value.value : null;
        const value = object && typeof object === 'object' && !Array.isArray(object) ? object[field] : undefined;
        return value === undefined || value === null ? undefined : {state: 'known' as const, value, evidence_ids: ref ? [ref.evidence_id] : []};
      })})) : parameterRows(data, dimension);
    return params.map((row, index) => {
      const present = row.values.filter(v => v?.state === 'known').map(v => v?.state === 'known' ? JSON.stringify(v.value) : '');
      const differs = new Set(present).size > 1;
      const complete = present.length === data.selections.length;
      const group = differs ? 'Con diferencias' : complete ? 'Sin diferencias' : 'Comparables';
      return {...row, dimension, results, group, key: `${dimension}:${index}`, complete};
    });
  });
  return <>
    <p>Las diferencias experimentales no implican incompatibilidad. “Comparables” reúne parámetros cuya comparación requiere advertencias o evidencia adicional; cada celda conserva su estado.</p>
    <div className="report-table-scroll" tabIndex={0} role="region" aria-label="Tabla A1–A6"><table className="report-data-table scc-preflight-table">
      <caption>Configuración experimental y evidencia A1–A6</caption>
      <thead><tr><th scope="col">Parámetro</th><th scope="col">Estado o diferencia</th>{data.selections.map((selection, index) => <th scope="col" key={selection.selection_id}>RUN {String.fromCharCode(65 + index)}<br /><small>{architecture(data, selection)}</small></th>)}</tr></thead>
      {['Con diferencias', 'Comparables', 'Sin diferencias'].map(group => <tbody key={group}>
        <tr><th colSpan={data.selections.length+2}><button className="ds-button" aria-expanded={groups.includes(group)} onClick={() => setGroups(old => old.includes(group) ? old.filter(g => g !== group) : [...old, group])}>{group} · {rows.filter(r => r.group === group).length}</button></th></tr>
        {groups.includes(group) && rows.filter(r => r.group === group).map(row => <Fragment key={row.key}>
          <tr><th scope="row"><button className="ds-button" aria-expanded={expanded.includes(row.key)} onClick={() => setExpanded(old => old.includes(row.key) ? old.filter(k => k !== row.key) : [...old, row.key])}>{row.dimension} · {row.label}</button></th><td>{row.group === 'Con diferencias' ? 'Diferencia experimental' : row.complete ? 'Valores coincidentes' : 'Evidencia parcial'}</td>
            {row.values.map((v, i) => <td key={i}>{v?.state === 'known' ? row.technical ? 'Identidad registrada' : typeof v.value === 'object' ? 'Configuración persistida' : jsonText(v.value) : v?.state === 'query_error' ? 'Error de consulta' : 'Sin evidencia'}</td>)}
          </tr>
          {expanded.includes(row.key) && <tr className="scc-expanded-row"><th scope="row">Detalle comparativo completo</th><td>{row.results.map(r => <div key={r.scope.scope_id}><VerdictBadge verdict={r.verdict} />{r.findings.map(f => <p key={f.reason_id}>{f.message}</p>)}</div>)}</td>{data.selections.map((selection,i) => <td key={selection.selection_id}><p>{row.values[i] ? observationText(row.values[i]!) : 'Sin evidencia'}</p><EvidenceCell data={data} selection={selection} dimension={row.dimension} /></td>)}</tr>}
        </Fragment>)}
      </tbody>)}
    </table></div>
    <ComparisonPython data={data} />
    <details><summary>Identificadores y fuentes A1–A6</summary>{data.selections.map(selection => <div key={selection.selection_id}><code className="report-identifier">{selection.training_run_id}</code><CopyText text={selection.training_run_id} label="Copiar UUID" />{(Object.keys(dimensions) as Dimension[]).map(dimension => <div key={dimension}><h4>{dimension} — {dimensions[dimension]}</h4><EvidenceCell data={data} selection={selection} dimension={dimension} /></div>)}</div>)}</details>
    <details><summary>Diagnóstico técnico por análisis</summary>
    {data.dimensions.map(d => <section key={d.scope.scope_id}><h4>{d.dimension}</h4><VerdictBadge verdict={d.verdict} />{d.findings.map(f => <p key={f.reason_id}>{f.message} · {f.condition}<br /><code>{f.code} · {f.evidence_ids.join(', ')}</code></p>)}</section>)}
    {data.analyses.map(analysis => <details key={analysis.analysis_id} className="report-evidence"><summary>{modules[analysis.module_id]} · <VerdictBadge verdict={analysis.verdict} /></summary><code>{verdictText(analysis.verdict)}</code>
      <p>{analysis.scope.question} · Población: {analysis.scope.population}</p>
      <p className="report-identifier">Participantes: {analysis.scope.participating_training_run_ids.join(', ') || 'Sin evidencia'}</p>
      {analysis.findings.map(finding => <p key={finding.reason_id}>{finding.message}</p>)}
      {analysis.interpretation_limits.map(limit => <p key={limit}>{limit}</p>)}
      {analysis.individual_data.map(item => <p key={item.selection_id} className="report-identifier">{item.selection_id}: {observationText(item.availability)} · Referencias: {item.references.join(', ') || 'No disponible'}</p>)}
    </details>)}</details>
  </>;
}

function ComparisonModules({ ids, datasource, selections, revision, onEvidenceChange }: { ids: string[]; datasource: string; selections: RequestedSelection[]; revision: number; onEvidenceChange: () => void }) {
  const [xaiVisited, setXaiVisited] = useState(false);
  const [scienceOpen, setScienceOpen] = useState(false);
  const [xaiOpen, setXaiOpen] = useState(false);
  return <>
    <details className="ds-accordion" onToggle={event => { setScienceOpen(event.currentTarget.open); setXaiOpen(event.currentTarget.open); if (event.currentTarget.open) setXaiVisited(true); }}><summary>Explicabilidad XAI</summary>
      {xaiVisited && ids.map((id, index) => <section key={id}><h3>RUN {String.fromCharCode(65+index)}</h3><PersistedXAI key={JSON.stringify([selections.find(s => s.training_run_id === id), revision])} selection={selections.find(s => s.training_run_id === id) ?? {training_run_id: id}} datasource={datasource} active={scienceOpen && xaiOpen} /><TrainingAssessmentXAI key={JSON.stringify([datasource, selections.find(selection => selection.training_run_id === id), revision])} trainingRunId={id} datasource={datasource} active={scienceOpen && xaiOpen} onEvidenceChange={onEvidenceChange} /></section>)}
    </details>

  </>;
}

function ComparisonEvidenceSession({ ids, datasource, maximum, selections }: { ids: string[]; datasource: string; maximum?: number; selections: RequestedSelection[] }) {
  const cache = useMemo(createComparisonCache, []);
  const [revision, setRevision] = useState(0);
  const [xaiRevision, setXaiRevision] = useState(0);
  const [detailOpen, setDetailOpen] = useState(false);
  const detailRef = useRef<HTMLDetailsElement>(null);
  const key = maximum !== undefined && ids.length >= 2 && ids.length <= maximum ? JSON.stringify(['preflight', datasource, selections, revision]) : null;
  const { data, error, loading } = useComparisonEvidence(cache, key, () => api.getComparisonPreflight(datasource, { selections }));
  const refresh = () => { cache.clear(); setRevision(value => value + 1); setXaiRevision(value => value + 1); };
  const findings = data ? [...new Map([...data.dimensions.flatMap(item => item.findings), ...data.analyses.flatMap(item => item.findings)].map(item => [item.reason_id, item])).values()] : [];
  return <>
    <section className="report-section" aria-label="Resumen metodológico" aria-busy={loading}>
      <div className="ds-page-header"><h2>Resumen metodológico</h2><button className="ds-button" onClick={refresh}>Actualizar evidencia</button></div>
      {!key && <p>Selecciona entre dos TRAIN y el máximo configurado para consultar el Preflight.</p>}
      {loading && <p role="status">Consultando Preflight…</p>}
      {error ? <ErrorMessage error={error} retry={refresh} /> : null}
      {data && <>
        <p>{data.selections.length} TRAIN participantes · {data.selections.map(selection => architecture(data, selection)).join(' / ')}</p>
        <p>{data.populations.find(p => p.complete.state === 'known' && p.complete.value === true)?.intersection_unique.state === 'known'
          ? `Población común acreditada para la selección. Consulte cobertura y resultados en cada módulo.`
          : 'La comparabilidad se determina por módulo; los resultados individuales permanecen disponibles.'}</p>
        <details><summary>Advertencias metodológicas y diagnóstico</summary>
          {groupWarnings(findings.filter(item => data.summary.warning_reason_ids.includes(item.reason_id))).map(group => <p key={group[0].reason_id}>{findingLabel(group[0])}</p>)}
          {data.consistency.limitations.map(limit => <p key={limit}>{limit}</p>)}
          <p>{data.evidence.length} referencias · Consulta: {data.generated_at}</p>
        </details>
        {data.technical_errors.map(item => <p role="alert" key={item.error_id}>ERROR_DE_CONSULTA · {item.message} · {item.operation} · {item.error_id}</p>)}
      </>}
      <button className="ds-button" onClick={() => { setDetailOpen(true); detailRef.current?.querySelector('summary')?.focus(); }}>¿Qué estamos comparando?</button>
    </section>
    <details ref={detailRef} className="ds-accordion" open={detailOpen} onToggle={event => setDetailOpen(event.currentTarget.open)}><summary>01 — ¿Qué estamos comparando?</summary>
      {data ? <PreflightEvidence data={data} /> : <p>El detalle utiliza la misma consulta del resumen metodológico.</p>}
    </details>
    <ScientificResults cache={cache} datasource={datasource} selections={selections} evidenceRevision={revision} />
    <ComparisonModules selections={selections} revision={xaiRevision} ids={ids} datasource={datasource} onEvidenceChange={() => { cache.clear(); setRevision(value => value + 1); }} />
    <ScientificRepresentations cache={cache} datasource={datasource} selections={selections} evidenceRevision={revision} />
    <ScientificQuestions cache={cache} datasource={datasource} selections={selections} evidenceRevision={revision} />
  </>;
}

export function ScientificPreflight(props: { ids: string[]; datasource: string; maximum?: number; selections: RequestedSelection[] }) {
  const { user, status } = useAuth();
  // Remount all retained evidence on a change of user, permissions, datasource or TRAIN set.
  const scope = JSON.stringify([user, status, props.datasource, props.ids]);
  return <Fragment key={scope}><ComparisonEvidenceSession {...props} /></Fragment>;
}
