import { ScientificResults, ScientificQuestions, ScientificRepresentations, PersistedXAI } from './ScientificReport';
import { ComparisonPython, configurationLabels, CopyText } from './ComparisonPython';
import { Fragment, useMemo, useState } from 'react';
import { useAuth } from '../../auth';
import { api, ApiError } from '../../services/api';
import { useComparisonEvidence } from '../../hooks/useComparisonEvidence';
import { createComparisonCache, type ComparisonCache } from '../../utils/comparisonCache';
import type { Dimension, EffectiveSelection, Finding, JsonValue, PopulationMember, Module, Observation, PreflightResponse, RequestedSelection, Verdict } from '../../types/scientificPreflight';
import { compareValues, projectField, classifyFields, evaluationDetails, type DetailField } from '../../utils/preflightPresentation';
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
    {selected && <div>{dimension === 'A1' ? 'dataset_version_id' : dimension === 'A2' ? 'Partición' : dimension === 'A5' ? 'Checkpoint seleccionado' : 'Identidad de evaluación'}: <ParameterValue value={selected} /></div>}
    {refs.map(ref => <div key={ref.evidence_id} id={evidenceTarget(selection.selection_id, ref.evidence_id)} tabIndex={-1}><ParameterValue value={ref.value} /><small>{ref.operation} · {ref.evidence_id} · {ref.verification === 'not_verified' ? 'No verificado' : 'Evidencia operacional'} · {ref.observed_at}</small></div>)}
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
interface ParameterRow { label: string; technical?: boolean; values: (Observation | undefined)[]; details?: DetailField[] }
function parameterRows(data: PreflightResponse, dimension: Dimension): ParameterRow[] {
  const selected = (label: string, field: 'dataset_version_id' | 'split' | 'checkpoint' | 'evaluation', technical = false) => ({ label, technical, values: data.selections.map(selection => selection[field]) });
  const projected = (source: Dimension, field: string, label: string) => ({ label, values: data.selections.map(selection => projectField(data, source, selection.selection_id, field)) });
  if (dimension === 'A1') return [selected('Versión del dataset', 'dataset_version_id', true), ...Object.entries({ name: 'Dataset', status: 'Estado del dataset', grouping_strategy: 'Estrategia', split_algorithm: 'Algoritmo de split', random_seed: 'Semilla de split', source_record_count: 'Registros oficiales' }).map(([field, label]) => projected('A1', field, label))];
  if (dimension === 'A2') return [selected('Partición evaluada', 'split'), projected('A2', 'counts', 'Particiones oficiales'), projected('A2', 'checks', 'Controles de validación del split'), ...Object.entries({ materialization_id: 'Materialización', materialization_status: 'Estado de materialización', reconciliation_status: 'Reconciliación', record_count: 'Registros materializados', materialization_dataset_matches: 'Materialización de la misma versión', 'campaign_snapshot.clinical_identity_fingerprint': 'Huella de identidad clínica', 'campaign_snapshot.record_assignment_fingerprint': 'Huella de asignación de registros', 'campaign_snapshot.source_population_fingerprint': 'Huella de población fuente', 'campaign_snapshot.patient_assignment_fingerprint': 'Huella de asignación de pacientes', consumed_images: 'Consumo registrado de imágenes' }).map(([field, label]) => projected('A2', field, label))];
  if (dimension === 'A6') {
    const fields = evaluationDetails(data);
    const scientific = fields.slice(0, 8);
    const values = data.selections.map((_, index): Observation => {
      const entries = scientific.map(field => [field.label, field.values[index]] as const);
      const error = entries.find(([, value]) => value?.state === 'query_error')?.[1];
      if (error) return error;
      return { state: 'known', value: Object.fromEntries(entries.map(([label, value]) => [label, value?.state === 'known' ? value.value : null])), evidence_ids: [] };
    });
    return [selected('Evaluación e intento', 'evaluation', true), projected('A6', 'protocol_hash', 'Huella de protocolo'),
    { label: 'Protocolo y regla de decisión', values, details: fields }];
  }
  if (dimension === 'A5') return [selected('Checkpoint atribuido', 'checkpoint', true), ...Object.entries({ selected_epoch: 'Época seleccionada', policy: 'Política de selección', metric: 'Métrica de selección', checksum_registered: 'Checksum registrado (sin verificación física)' }).map(([field, label]) => ({ ...projected('A5', field, label), technical: field === 'checksum_registered' })), ...(['registered', 'lineage'] as const).map(field => ({ label: field === 'registered' ? 'Registro de checkpoint' : 'Linaje', values: data.selections.map(selection => data.checkpoints.find(check => check.selection_id === selection.selection_id)?.[field]) }))];
  if (dimension === 'A3') return [...data.populations.flatMap((population, index) => Object.entries(populationLabels).map(([field, label]) => ({ label: `${data.populations.length > 1 ? `Población ${index + 1} · ` : ''}${label}`, values: data.selections.map(selection => field === 'intersection_unique' ? population.intersection_unique : field === 'complete' ? population.complete : population.per_selection.find(member => member.selection_id === selection.selection_id)?.[field as keyof typeof populationLabels & keyof PopulationMember]) })))];
  return [];
}

export function CompactValue({ value }: { value: JsonValue }) {
  if (typeof value === 'string' && /^[a-f0-9-]{32,}$/i.test(value)) return <span className="scc-compact-id">
    <code title={value} aria-label={value}>{value.slice(0, 8)}…{value.slice(-6)}</code>
    <CopyText key={value} text={value} label="Copiar identificador" iconOnly />
  </span>;
  if (value && typeof value === 'object') {
    const entries = Object.entries(value);
    if (!entries.length) return <span>Sin evidencia (sin entradas)</span>;
    const list = (items: typeof entries) => <ul className="scc-composite-value">{items.map(([key, item]) => <li key={key}>
      {!Array.isArray(value) && <span className="scc-key">{key}: </span>}
      <div className="scc-val"><CompactValue value={item} /></div>
    </li>)}</ul>;
    return <div>{list(entries.slice(0, 6))}{entries.length > 6 && <details><summary>Más datos ({entries.length - 6})</summary>{list(entries.slice(6))}</details>}</div>;
  }
  return <span className="scc-val">{value === '' ? 'Sin evidencia (vacío)' : jsonText(value)}</span>;
}
function ParameterValue({ value }: { value: Observation | undefined }) {
  return value?.state === 'known' ? <CompactValue value={value.value} /> : <span>{value ? observationText(value) : 'Sin evidencia'}</span>;
}
function ConsolidatedFindings({ data }: { data: PreflightResponse }) {
  const sourceFindings = [...data.dimensions.flatMap(result => result.findings), ...data.analyses.flatMap(result => result.findings)];
  const findings = [...new Map([...sourceFindings].reverse().map(finding => [finding.reason_id, finding])).values()];
  const affected = (items: Finding[]) => data.selections.flatMap((selection, index) => items.some(item => item.affected_selection_ids.includes(selection.selection_id)) ? [`RUN ${String.fromCharCode(65 + index)}`] : []).join(', ');
  return <div className="scc-findings">
    {groupWarnings(findings).map(items => <div key={items[0].reason_id}><p>{items[0].message} · afecta a {affected(items) || 'alcance indicado en la evidencia'}</p><p>{items[0].condition}</p><code className="report-identifier">{items[0].code} · Motivos: {items.map(item => item.reason_id).join(', ')} · Evidencia: {[...new Set(items.flatMap(item => item.evidence_ids))].join(', ')}</code><ul>{items.map(item => <li key={item.reason_id}><code>{item.reason_id}</code> · {affected([item])} · <code>{item.evidence_ids.join(', ')}</code></li>)}</ul></div>)}
  </div>;
}

function evidenceTarget(selectionId: string, reference: string) {
  return `scc-evidence-${encodeURIComponent(selectionId)}-${encodeURIComponent(reference)}`;
}
function ConsolidatedDetail({ fields, data }: { fields: DetailField[]; data: PreflightResponse }) {
  const classified = classifyFields(fields);
  const shared = classified.filter(field => field.group === 'Sin diferencias');
  const other = classified.filter(field => field.group !== 'Sin diferencias' && field.values.some(value => value?.state === 'known'));
  const absent = classified.filter(field => !shared.includes(field) && !other.includes(field));
  const missingGroups = new Map<string, { text: string; runs: string[]; fields: string[] }>();
  for (const field of absent) {
    const byReason = new Map<string, string[]>();
    field.values.forEach((value, i) => {
      const text = value ? observationText(value) : 'Sin evidencia';
      byReason.set(text, [...(byReason.get(text) ?? []), `RUN ${String.fromCharCode(65 + i)}`]);
    });
    for (const [text, runs] of byReason) {
      const key = JSON.stringify([text, runs]);
      const previous = missingGroups.get(key);
      missingGroups.set(key, { text, runs, fields: [...(previous?.fields ?? []), field.label] });
    }
  }
  return <div className="scc-consolidated-detail">
    {shared.length > 0 && <dl className="ds-dl ds-dl--rows">{shared.map(field => <div key={field.label}><dt>{field.label}</dt><dd><ParameterValue value={field.values[0]} /></dd></div>)}</dl>}
    {other.length > 0 && <div className="report-table-scroll" tabIndex={0} role="region" aria-label="Diferencias por RUN"><table className="report-data-table"><caption>Diferencias y evidencia parcial por RUN</caption><thead><tr><th scope="col">Campo</th>{data.selections.map((selection, i) => <th scope="col" key={selection.selection_id}>RUN {String.fromCharCode(65 + i)}</th>)}</tr></thead><tbody>{other.map(field => <tr key={field.label}><th scope="row">{field.label}</th>{field.values.map((value, i) => <td key={data.selections[i].selection_id} data-match={field.matches[i]}><ParameterValue value={value} /></td>)}</tr>)}</tbody></table></div>}
    {[...missingGroups].map(([key, missing]) => <p key={key}>{missing.fields.join(', ')}: {missing.text} · {missing.runs.join(', ')}</p>)}
  </div>;
}
export function PartitionCards({ data }: { data: PreflightResponse }) {
  const field = (source: Dimension, key: string, label: string): DetailField => ({ label, values: data.selections.map(selection => projectField(data, source, selection.selection_id, key)) });
  const dataset = parameterRows(data, 'A1');
  const partition = parameterRows(data, 'A2');
  const cards: { title: string; fields: DetailField[] }[] = [
    { title: 'Dataset', fields: dataset.slice(0, 3) },
    { title: 'Partición', fields: [...dataset.slice(3, 6), partition[0]] },
    { title: 'Distribución', fields: [field('A2', 'counts.train', 'TRAIN'), field('A2', 'counts.val', 'VAL'), field('A2', 'counts.test', 'TEST'), dataset[6]] },
    { title: 'Materialización', fields: partition.filter(row => ['Estado de materialización', 'Reconciliación', 'Registros materializados', 'Materialización de la misma versión'].includes(row.label)) },
    { title: 'Integridad', fields: [{ label: 'Número de verificaciones', values: data.selections.map(selection => {
      const checks = projectField(data, 'A2', selection.selection_id, 'checks');
      return checks?.state === 'known' && Array.isArray(checks.value) ? { ...checks, value: checks.value.length } : checks;
    }) }, { label: 'Resultados registrados', values: data.selections.map(selection => {
      const checks = projectField(data, 'A2', selection.selection_id, 'checks');
      if (checks?.state !== 'known' || !Array.isArray(checks.value)) return checks;
      const counts = { PASS: 0, FAIL: 0, 'Evidencia insuficiente': 0 };
      for (const check of checks.value) {
        const status = check && typeof check === 'object' && !Array.isArray(check) ? check.status : null;
        counts[status === 'PASS' || status === 'FAIL' ? status : 'Evidencia insuficiente']++;
      }
      return checks.value.length ? { ...checks, value: counts } : undefined;
    }) }] },
  ];
  return <section aria-label="Dataset y partición"><h3>A1 · Dataset y A2 · Partición</h3>
    <div className="scc-partition-cards">{cards.map(card => <section className="ds-section" key={card.title}><h4>{card.title} {['Dataset', 'Partición'].includes(card.title) && data.dimensions.filter(item => item.dimension === (card.title === 'Dataset' ? 'A1' : 'A2')).map(item => <VerdictBadge key={item.scope.scope_id} verdict={item.verdict} />)}</h4><ConsolidatedDetail fields={card.fields} data={data} />{card.title === 'Integridad' && <details><summary>Comprobaciones registradas</summary><ConsolidatedDetail fields={[partition[2]]} data={data} /></details>}</section>)}
      <section className="ds-section"><h4>Trazabilidad</h4><details><summary>Identificadores y fingerprints</summary><ConsolidatedDetail data={data} fields={[
        partition[3], ...partition.filter(row => row.label.startsWith('Huella')),
        field('A2', 'campaign_id', 'Campaña · procedencia'), field('A2', 'campaign_dataset_version_id', 'Versión de dataset de campaña'),
      ]} /></details><p>Fuentes completas en Detalle técnico y trazabilidad.</p></section>
    </div>
    <p>La partición gobernada no acredita por sí sola el consumo individual de imágenes durante TRAIN. La población de evaluación alineada se documenta en A3.</p>
    <ConsolidatedDetail fields={[partition[partition.length - 1]]} data={data} />
  </section>;
}

export function MethodologicalWarnings({ data, findings }: { data: PreflightResponse; findings: Finding[] }) {
  // Presentation aggregate only; individual scientific verdicts remain authoritative.
  const states: string[] = [...data.dimensions, ...data.analyses].map(item => verdictText(item.verdict));
  const state = ['NO_COMPARABLE', 'ERROR_DE_CONSULTA', 'EVIDENCIA_INSUFICIENTE', 'COMPARABLE_CON_ADVERTENCIAS', 'COMPARABLE'].find(item => states.includes(item)) ?? 'EVIDENCIA_INSUFICIENTE';
  const warnings = findings.filter(item => data.summary.warning_reason_ids.includes(item.reason_id) && item.code !== 'CONFIGURATION_INCOMPLETE');
  return <details className="ds-accordion"><summary><span className="scc-verdict scc-methodology-state" data-state={state}>Advertencias metodológicas y diagnóstico · {stateLabels[state]}</span></summary>
    {groupWarnings(warnings).map(group => {
      const finding = group[0];
      const field = finding.code.startsWith('CONFIGURATION_DIFFERENCE_') ? finding.code.slice('CONFIGURATION_DIFFERENCE_'.length).toLowerCase() : '';
      return <div key={finding.reason_id}>{field ? <div>{configurationLabels[field] ?? field}{data.selections.map((selection, i) => <Fragment key={selection.selection_id}> · RUN {String.fromCharCode(65 + i)}: <ParameterValue value={projectField(data, 'A4', selection.selection_id, field)} /></Fragment>)}</div>
        : <p>{finding.code === 'DEVELOPMENT_VALIDATION' ? 'La VALIDATION final de desarrollo indicada en la evidencia histórica no equivale a TEST independiente. Las evaluaciones independientes seleccionadas conservan su propio split, propósito y protocolo en A6.' : findingLabel(finding)}</p>}</div>;
    })}
    {data.selections.some(selection => selection.split.state === 'known' && selection.split.value === 'val') && !warnings.some(item => item.code === 'DEVELOPMENT_VALIDATION') && <p>Las evaluaciones seleccionadas sobre VAL, incluidas las independientes, no equivalen a TEST independiente. Su propósito y protocolo se conservan en A6.</p>}
  </details>;
}

function AvailabilityMatrix({ data }: { data: PreflightResponse }) {
  return <div className="report-table-scroll" tabIndex={0} role="region" aria-label="Disponibilidad por análisis"><table className="report-data-table scc-preflight-table"><caption>Diagnóstico por análisis · participantes: {data.selections.map((_, i) => `RUN ${String.fromCharCode(65 + i)}`).join(', ')}</caption>
    <thead><tr><th scope="col">Análisis</th><th scope="col">Estado</th><th scope="col">Advertencia principal</th>{data.selections.map(selection => <th scope="col" key={selection.selection_id}>RUN {String.fromCharCode(65 + data.selections.indexOf(selection))}</th>)}</tr></thead>
    <tbody>{data.analyses.map(analysis => <tr key={analysis.analysis_id}><th scope="row">{modules[analysis.module_id]}</th><td><VerdictBadge verdict={analysis.verdict} /><code>{verdictText(analysis.verdict)}</code></td>
      <td>{analysis.findings[0] ? findingLabel(analysis.findings[0]) : 'Sin advertencias registradas'}{groupWarnings(analysis.findings).length > 1 && ` · ${groupWarnings(analysis.findings).length} causas (ver motivos técnicos)`}<details><summary>Motivos técnicos</summary><p>{analysis.scope.question} · Población: {analysis.scope.population}</p><p>{analysis.findings.map(finding => finding.reason_id).join(', ')}</p>{analysis.interpretation_limits.map(limit => <p key={limit}>{limit}</p>)}<p>Referencias: {analysis.evidence_ids.join(', ') || 'Sin evidencia'}</p></details></td>
      {data.selections.map(selection => {
        const item = analysis.individual_data.find(item => item.selection_id === selection.selection_id);
        const participating = analysis.scope.selection_ids.includes(selection.selection_id);
        return <td key={selection.selection_id}>{!participating && <p>Fuera del alcance del análisis</p>}{item ? <><ParameterValue value={item.availability} /><details><summary>Referencias</summary>{item.references.join(', ') || 'Sin evidencia'}</details></> : 'Sin evidencia'}</td>;
      })}</tr>)}</tbody></table></div>;
}

export function PreflightEvidence({ data }: { data: PreflightResponse }) {
  const [expanded, setExpanded] = useState<string[]>([]);
  const [groups, setGroups] = useState(['Con diferencias', 'Comparables']);
  const selectionKey = JSON.stringify([data.correlation_id, data.selections]);
  const rows = (Object.keys(dimensions) as Dimension[]).flatMap(dimension => {

    const params: ParameterRow[] = dimension === 'A4' ? Object.entries(configurationLabels).map(([field, label]) => ({
      label, technical: false,
      values: data.selections.map(selection => projectField(data, 'A4', selection.selection_id, field))
    })) : parameterRows(data, dimension);
    return params.filter(row => dimension !== 'A1' && dimension !== 'A2' && !row.technical).map((row, index) => ({ ...row, dimension, ...compareValues(row.values), key: `${selectionKey}:${dimension}:${index}` }));
  });
  return <>
    <p>Las diferencias experimentales no implican incompatibilidad. “Comparables” reúne parámetros cuya comparación requiere advertencias o evidencia adicional; cada celda conserva su estado.</p>
    <PartitionCards data={data} />
    {['Con diferencias', 'Comparables', 'Sin diferencias'].map(group => {
      const shared = group === 'Sin diferencias';
      const partial = group === 'Comparables';
      const groupRows = rows.filter(row => row.group === group);
      const columns = shared ? 3 : data.selections.length + (partial ? 2 : 1);
      return <section className="scc-parameter-group" key={group}>
        <button className="ds-button" aria-expanded={groups.includes(group)} onClick={() => setGroups(old => old.includes(group) ? old.filter(g => g !== group) : [...old, group])}>{group} · {groupRows.length}</button>
        {groups.includes(group) && <>
          <div className="report-table-scroll" tabIndex={0} role="region" aria-label={`${group} A1–A6`}><table className="report-data-table scc-preflight-table scc-parameter-table">
            <caption>{group} · parámetros de los RUN seleccionados</caption>
            <thead><tr>{shared && <th scope="col">Módulo</th>}<th scope="col">Parámetro</th>{partial && <th scope="col">Estado</th>}{shared ? <th scope="col">Valor compartido</th> : data.selections.map((selection, index) => <th scope="col" key={selection.selection_id}>RUN {String.fromCharCode(65 + index)}<br /><small>{architecture(data, selection)}</small></th>)}</tr></thead>
            {(Object.keys(dimensions) as Dimension[]).map(dimension => {
              const moduleRows = groupRows.filter(row => row.dimension === dimension);
              return moduleRows.length > 0 && <tbody key={dimension}>{moduleRows.map((row, index) => <Fragment key={row.key}>
                <tr>{shared && index === 0 && <th scope="rowgroup" rowSpan={moduleRows.length + moduleRows.filter(item => item.details && expanded.includes(item.key)).length}><span className="scc-module-badge">{dimension}</span><small>{dimensions[dimension]}</small></th>}
                  <th scope="row">{row.details ? <button className="ds-button" aria-expanded={expanded.includes(row.key)} onClick={() => setExpanded(old => old.includes(row.key) ? old.filter(k => k !== row.key) : [...old, row.key])}>{row.dimension} · {row.label}</button> : <>{row.dimension} · {row.label}</>}{row.dimension === 'A2' && row.details && <small> · Diferencia de procedencia</small>}</th>
                  {partial && <td>{row.values.some(value => value?.state === 'query_error') ? 'ERROR_DE_CONSULTA' : 'Evidencia parcial'}</td>}
                  {shared ? <td>{row.details && row.dimension === 'A6' ? <ConsolidatedDetail fields={row.details.slice(0, 5)} data={data} /> : <ParameterValue value={row.values[0]} />}<span className="scc-equal">{data.selections.map((_, i) => String.fromCharCode(65 + i)).join('=')}</span></td>
                    : row.details && row.dimension === 'A6' ? <td colSpan={data.selections.length}><ConsolidatedDetail fields={row.details.slice(0, 5)} data={data} /></td>
                      : row.values.every(value => !value || value.state === 'unknown' || (value.state === 'known' && value.value === null)) ? <td colSpan={data.selections.length}>Sin evidencia suficiente en los {data.selections.length} RUN</td>
                        : row.values.map((value, i) => <td key={data.selections[i].selection_id} data-match={row.matches[i]} data-match-tone={row.matches[i] ? [...new Set(row.matches.filter(Boolean))].indexOf(row.matches[i]) % 2 : undefined} title={row.matches[i] ? `Coinciden: ${row.matches[i]!.split('').join('=')}` : undefined}><ParameterValue value={value} />

                        </td>)}
                </tr>
                {row.details && expanded.includes(row.key) && <tr className="scc-expanded-row"><td colSpan={columns - (shared ? 1 : 0)}><ConsolidatedDetail fields={row.dimension === 'A6' ? row.details.slice(5) : row.details} data={data} /></td></tr>}
              </Fragment>)}</tbody>;
            })}
          </table></div>
          {groupRows.length === 0 && <p>No hay parámetros en este grupo.</p>}
          <p className="scc-meta">{shared ? 'Valores acreditados compartidos entre los RUN seleccionados. Un consumo registrado de cero indica que no hay registros de consumo individual en la fuente consultada; no demuestra ausencia de entrenamiento.' : partial ? 'La ausencia uniforme de evidencia no discrimina entre RUN, pero limita la comparación de este parámetro. Los errores de consulta conservan su condición técnica.' : 'La época seleccionada corresponde al checkpoint, no al total ejecutado.'}</p>
        </>}
      </section>;
    })}
    <ComparisonPython data={data} />
    <details className="ds-accordion"><summary>Detalle técnico y trazabilidad</summary><p>Consulta: {data.generated_at}</p>{data.consistency.limitations.map(limit => <p key={limit}>{limit}</p>)}
      <details><summary>Identificadores y fuentes A1–A6</summary>{data.selections.map((selection, index) => <section key={selection.selection_id}><h3>Trazabilidad técnica · RUN {String.fromCharCode(65 + index)}</h3><CompactValue value={selection.training_run_id} />{(Object.keys(dimensions) as Dimension[]).map(dimension => <div key={dimension} id={evidenceTarget(selection.selection_id, dimension)} tabIndex={-1}><h4>{dimension} — {dimensions[dimension]} {data.dimensions.filter(item => item.dimension === dimension).map(item => <VerdictBadge key={item.scope.scope_id} verdict={item.verdict} />)}</h4><EvidenceCell data={data} selection={selection} dimension={dimension} /></div>)}{data.evidence.filter(ref => !(ref.source in dimensions) && ref.selection_ids.includes(selection.selection_id)).map(ref => <div key={ref.evidence_id}><h4>{ref.source}</h4><ParameterValue value={ref.value} /><small>{ref.evidence_id} · {ref.operation} · {ref.verification} · {ref.observed_at}</small></div>)}</section>)}</details>
      <details><summary>Diagnóstico técnico por análisis</summary>
        <ConsolidatedFindings data={data} />
        <AvailabilityMatrix data={data} /></details>
      {data.technical_errors.map(error => <p key={error.error_id}>{error.error_id} · {error.message} · {error.operation}</p>)}
    </details>
  </>;
}

function ComparisonModules({ ids, datasource, selections, revision, onEvidenceChange }: { ids: string[]; datasource: string; selections: RequestedSelection[]; revision: number; onEvidenceChange: () => void }) {
  const [xaiVisited, setXaiVisited] = useState(false);
  const [scienceOpen, setScienceOpen] = useState(false);
  const [xaiOpen, setXaiOpen] = useState(false);
  return <>
    <details className="ds-accordion" onToggle={event => { setScienceOpen(event.currentTarget.open); setXaiOpen(event.currentTarget.open); if (event.currentTarget.open) setXaiVisited(true); }}><summary>Explicabilidad XAI</summary>
      {xaiVisited && ids.map((id, index) => <section key={id}><h3>RUN {String.fromCharCode(65 + index)}</h3><PersistedXAI key={JSON.stringify([selections.find(s => s.training_run_id === id), revision])} selection={selections.find(s => s.training_run_id === id) ?? { training_run_id: id }} datasource={datasource} active={scienceOpen && xaiOpen} /><TrainingAssessmentXAI key={JSON.stringify([datasource, selections.find(selection => selection.training_run_id === id), revision])} trainingRunId={id} datasource={datasource} active={scienceOpen && xaiOpen} onEvidenceChange={onEvidenceChange} /></section>)}
    </details>

  </>;
}

function ComparisonEvidenceSession({ ids, datasource, maximum, selections }: { ids: string[]; datasource: string; maximum?: number; selections: RequestedSelection[] }) {
  const cache = useMemo(createComparisonCache, []);
  const [revision, setRevision] = useState(0);
  const [xaiRevision, setXaiRevision] = useState(0);
  const [detailOpen, setDetailOpen] = useState(false);
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
        <p className="scc-meta">{data.evidence.length} referencias</p>
        <p>{data.selections.length} TRAIN participantes · {data.selections.map(selection => architecture(data, selection)).join(' / ')}</p>
        <p>{data.populations.find(p => p.complete.state === 'known' && p.complete.value === true)?.intersection_unique.state === 'known'
          ? `Población común acreditada para la selección. Consulte cobertura y resultados en cada módulo.`
          : 'La comparabilidad se determina por módulo; los resultados individuales permanecen disponibles.'}</p>
        <MethodologicalWarnings data={data} findings={findings} />
        {data.technical_errors.map(item => <p role="alert" key={item.error_id}>ERROR_DE_CONSULTA · {item.message} · {item.operation} · {item.error_id}</p>)}
      </>}
    </section>
    <details className="ds-accordion" open={detailOpen} onToggle={event => setDetailOpen(event.currentTarget.open)}><summary>01 — ¿Qué estamos comparando?</summary>
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
