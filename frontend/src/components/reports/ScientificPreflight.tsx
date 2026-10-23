import { DatasetIntegrity } from './DatasetIntegrity';
import { CurvesModule, MetricsModule, ConsensusModule, ScientificQuestions, PersistedXAI } from './ScientificReport';
import { ScientificRepresentations } from './ScientificRepresentations';
import { AnalysisPanel, AnalysisSectionNav, analysisSections, defaultAnalysisSection, useVisitedSections, type AnalysisSection } from './AnalysisWorkspace';
import { ComparisonPython, configurationLabels, CopyText } from './ComparisonPython';
import { Fragment, useMemo, useState } from 'react';
import { useAuth } from '../../auth';
import { api, ApiError } from '../../services/api';
import { useComparisonEvidence } from '../../hooks/useComparisonEvidence';
import { createComparisonCache, type ComparisonCache } from '../../utils/comparisonCache';
import type { Dimension, EffectiveSelection, Finding, JsonValue, PopulationMember, Module, Observation, PreflightResponse, RequestedSelection, Verdict } from '../../types/scientificPreflight';
import { equalityKey, compareValues, projectField, classifyFields, evaluationDetails, missingEvidence, openEvidenceTarget, type DetailField } from '../../utils/preflightPresentation';
import { executorLabel, useExplainExecutor } from '../../hooks/useExplainExecutor';

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
    {refs.map(ref => <div key={ref.evidence_id} id={evidenceTarget(selection.selection_id, ref.evidence_id)} tabIndex={-1}><ParameterValue value={ref.value} />{Object.keys(ref.record_keys).length > 0 && <details><summary>Claves de procedencia</summary><CompactValue value={ref.record_keys} /></details>}<small>{ref.operation} · {ref.evidence_id} · {ref.verification === 'not_verified' ? 'No verificado' : 'Evidencia operacional'} · {ref.observed_at}</small></div>)}
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
    return [selected('Evaluación e intento', 'evaluation', true), { ...projected('A6', 'protocol_hash', 'Huella de protocolo'), technical: true },
    { label: 'Protocolo y regla de decisión', values, details: scientific.slice(5).some(field => field.values.some(value => equalityKey(value) !== undefined)) ? scientific : undefined }];
  }
  if (dimension === 'A5') return [selected('Checkpoint atribuido', 'checkpoint', true), ...Object.entries({ selected_epoch: 'Época seleccionada', policy: 'Política de selección', metric: 'Métrica de selección', checksum_registered: 'Checksum registrado (sin verificación física)' }).map(([field, label]) => ({ ...projected('A5', field, label), technical: field === 'checksum_registered' })), ...(['registered', 'lineage'] as const).map(field => ({ label: field === 'registered' ? 'Registro de checkpoint' : 'Linaje', values: data.selections.map(selection => data.checkpoints.find(check => check.selection_id === selection.selection_id)?.[field]) }))];
  if (dimension === 'A3') return [...data.populations.flatMap((population, index) => Object.entries(populationLabels).map(([field, label]) => ({ label: `${data.populations.length > 1 ? `Población ${index + 1} · ` : ''}${label}`, values: data.selections.map(selection => field === 'intersection_unique' ? population.intersection_unique : field === 'complete' ? population.complete : population.per_selection.find(member => member.selection_id === selection.selection_id)?.[field as keyof typeof populationLabels & keyof PopulationMember]) })))];
  return [];
}

export function CompactValue({ value }: { value: JsonValue | undefined }) {
  if (typeof value === 'string' && /^[a-f0-9-]{32,}$/i.test(value)) return <span className="scc-compact-id">
    <code title={value} aria-label={value}>{value.slice(0, 8)}…{value.slice(-6)}</code>
    <CopyText key={value} text={value} label="Copiar identificador" iconOnly />
  </span>;

  if (value && typeof value === 'object') {
    const entries = Object.entries(value);
    if (!entries.length) return <span>Sin evidencia (sin entradas)</span>;
    const populated: typeof entries = [];
    const empty: typeof entries = [];
    for (const entry of entries) {
      const item = typeof entry[1] === 'string' ? entry[1].trim().toLowerCase() : entry[1];
      const isEmpty = item == null || item === '' || item === 'sin evidencia' || item === 'n/a';
      (isEmpty ? empty : populated).push(entry);
    }

    const list = (items: typeof entries) => <ul className="scc-composite-value">{items.map(([key, item]) => <li key={key}>
      {!Array.isArray(value) && <span className="scc-key">{key}: </span>}
      <div className="scc-val"><CompactValue value={item} /></div>
    </li>)}</ul>;

    return <div>{populated.length > 0 && list(populated)}{empty.length > 0 && <details><summary>Más datos ({empty.length})</summary>{list(empty)}</details>}</div>;
  }

  return <span className="scc-val">{value === undefined ? 'Sin evidencia' : value === '' ? 'Sin evidencia (vacío)' : jsonText(value)}</span>;
}
function ParameterValue({ value }: { value: Observation | undefined }) {
  return value?.state === 'known' ? <CompactValue value={value.value} /> : <span>{value ? observationText(value) : 'Sin evidencia'}</span>;
}
function ConsolidatedFindings({ data }: { data: PreflightResponse }) {
  const sourceFindings = [...data.dimensions.flatMap(result => result.findings), ...data.analyses.flatMap(result => result.findings)];
  const findings = [...new Map([...sourceFindings.filter(finding => finding.kind !== 'missing')].reverse().map(finding => [finding.reason_id, finding])).values()];
  const affected = (items: Finding[]) => data.selections.flatMap((selection, index) => items.some(item => item.affected_selection_ids.includes(selection.selection_id)) ? [`RUN ${String.fromCharCode(65 + index)}`] : []).join(', ');
  return <div className="scc-findings">
    {groupWarnings(findings).map(items => <div key={items[0].reason_id}><p>{items[0].message} · afecta a {affected(items) || 'alcance indicado en la evidencia'}</p><p>{items[0].condition}</p><EvidenceLinks data={data} ids={[...new Set(items.flatMap(item => item.evidence_ids))]} /><code className="report-identifier">{items[0].code} · Motivos: {items.map(item => item.reason_id).join(', ')} · Evidencia: {[...new Set(items.flatMap(item => item.evidence_ids))].join(', ')}</code><ul>{items.map(item => <li key={item.reason_id}><code>{item.reason_id}</code> · {affected([item])} · <code>{item.evidence_ids.join(', ')}</code></li>)}</ul></div>)}
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
  return <div className="scc-consolidated-detail">
    {shared.length > 0 && <dl className="ds-dl ds-dl--rows">{shared.map(field => <div key={field.label}><dt>{field.label}</dt><dd><ParameterValue value={field.values[0]} /></dd></div>)}</dl>}
    {other.length > 0 && <div className="report-table-scroll" tabIndex={0} role="region" aria-label="Diferencias por RUN"><table className="report-data-table"><caption>Diferencias y evidencia parcial por RUN</caption><thead><tr><th scope="col">Campo</th>{data.selections.map((selection, i) => <th scope="col" key={selection.selection_id}>RUN {String.fromCharCode(65 + i)}</th>)}</tr></thead><tbody>{other.map(field => <tr key={field.label}><th scope="row">{field.label}</th>{field.values.map((value, i) => <td key={data.selections[i].selection_id} data-match={field.matches[i]}><ParameterValue value={value} /></td>)}</tr>)}</tbody></table></div>}
    {absent.length > 0 && <p>{absent.map(field => field.label).join(', ')}: {absent.some(field => field.values.some(value => value?.state === 'query_error')) ? `ERROR_DE_CONSULTA · ${[...new Set(absent.flatMap(field => field.values.flatMap(value => value?.state === 'query_error' ? value.error_ids : [])))].join(', ')}` : 'Sin evidencia completa'}. <button className="ds-button" onClick={() => openEvidenceTarget(document.getElementById('scc-missing-evidence'))}>Consultar causas e impacto</button></p>}
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
  ];
  return <section aria-label="Dataset y partición"><details className="ds-accordion"><summary>A1 · Dataset y A2 · Partición</summary>
    <div className="scc-partition-cards">{cards.map(card => <section className="ds-section" key={card.title}><h4>{card.title} {['Dataset', 'Partición'].includes(card.title) && data.dimensions.filter(item => item.dimension === (card.title === 'Dataset' ? 'A1' : 'A2')).map(item => <VerdictBadge key={item.scope.scope_id} verdict={item.verdict} />)}</h4><ConsolidatedDetail fields={card.fields} data={data} />{card.fields.some(field => compareValues(field.values).group === 'Con diferencias') && <p className="scc-meta">Diferencia de procedencia: consulte la población y el split de cada análisis antes de interpretar un contraste directo.</p>}</section>)}
      <DatasetIntegrity data={data} />
      <section className="ds-section"><h4>Trazabilidad</h4><button className="ds-button" onClick={() => openEvidenceTarget(document.getElementById('scc-technical-registry'))}>Consultar identificadores y fuentes</button><p>Dataset, campaña y fingerprints conservan su procedencia en el registro técnico.</p></section>
    </div>
    <p>La partición gobernada no acredita por sí sola el consumo individual de imágenes durante TRAIN. La población de evaluación alineada se documenta en A3.</p>
    <ConsolidatedDetail fields={[partition[partition.length - 1]]} data={data} />
  </details></section>;
}

export function MethodologicalWarnings({ data, findings }: { data: PreflightResponse; findings: Finding[] }) {
  const warnings = findings.filter(item => data.summary.warning_reason_ids.includes(item.reason_id) && item.code !== 'CONFIGURATION_INCOMPLETE');
  return <details className="ds-accordion"><summary>Advertencias metodológicas y diagnóstico</summary>
    <ul>{data.analyses.map(analysis => <li key={analysis.analysis_id}>{modules[analysis.module_id]} · {analysis.scope.question}: <VerdictBadge verdict={analysis.verdict} /></li>)}</ul>
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

export function MethodologicalSynthesis({ data }: { data: PreflightResponse }) {
  const states = Object.keys(stateLabels).flatMap(state => {
    const analyses = data.analyses.filter(analysis => verdictText(analysis.verdict) === state);
    return analyses.length ? [`${stateLabels[state]}: ${[...new Set(analyses.map(analysis => modules[analysis.module_id]))].join(', ')} (${analyses.length} ${analyses.length === 1 ? 'alcance' : 'alcances'})`] : [];
  });
  const differences = data.dimensions.filter(item => item.findings.some(finding => finding.kind === 'difference'));
  return <div className="scc-methodological-synthesis" aria-label="Síntesis de la comparación">
    <p>{states.join(' · ') || 'No hay dictámenes por análisis en esta respuesta.'}</p>
    <p>{differences.length ? `Diferencias documentadas: ${[...new Set(differences.map(item => `${item.dimension} · ${dimensions[item.dimension]}`))].join(', ')}. ` : ''}La configuración TRAIN describe variables experimentales; EVALUATE conserva su split y protocolo. La cobertura de EXPLAIN depende de los métodos y artefactos acreditados.</p>
    <button className="ds-button" onClick={() => openEvidenceTarget(document.getElementById('scc-analysis-diagnostics'))}>Consultar alcances y límites por análisis</button>
  </div>;
}

function EvidenceLinks({ data, ids }: { data: PreflightResponse; ids: string[] }) {
  return <>{ids.flatMap(id => {
    const ref = data.evidence.find(item => item.evidence_id === id);
    const selectionId = ref?.selection_ids.find(value => data.selections.some(selection => selection.selection_id === value));
    return ref && selectionId ? [<button key={id} className="ds-button" onClick={() => openEvidenceTarget(document.getElementById(evidenceTarget(selectionId, id)))}>Fuente: {ref.source} · {ref.operation}</button>] : [];
  })}</>;
}

export function EvidenceInventory({ data, fields }: { data: PreflightResponse; fields: DetailField[] }) {
  const entries = missingEvidence(data, fields);
  return <details className="ds-accordion" id="scc-missing-evidence"><summary>Inventario de evidencia pendiente y errores · {entries.length} causas por RUN</summary>
    <p>La ausencia de un dato no acredita que no se haya ejecutado o persistido. Los impactos se vinculan únicamente a los análisis referenciados por el preflight.</p>
    <div className="report-table-scroll" role="region" aria-label="Evidencia pendiente" tabIndex={0}><table className="report-data-table"><thead><tr>{['Evidencia', 'RUN', 'Causa', 'Impacto', 'Estado'].map(label => <th scope="col" key={label}>{label}</th>)}</tr></thead>
      <tbody>{entries.map((entry, index) => <tr key={index}><th scope="row">{entry.evidence.join(' · ')}<EvidenceLinks data={data} ids={entry.evidenceIds} /></th><td>{entry.selectionIds.map(id => `RUN ${String.fromCharCode(65 + data.selections.findIndex(selection => selection.selection_id === id))}`).join(', ') || 'Alcance de la consulta'}</td><td>{entry.cause}{entry.errorIds.length > 0 && <code className="report-identifier">{entry.errorIds.join(', ')}</code>}</td><td>{entry.analyses.map(id => { const analysis = data.analyses.find(item => item.analysis_id === id); return analysis ? `${modules[analysis.module_id]}: ${analysis.scope.question}` : id; }).join(' · ') || 'No se puede acreditar este dato; impacto por análisis no especificado.'}</td><td>{entry.state}</td></tr>)}</tbody>
    </table></div>{!entries.length && <p>Sin carencias registradas en los campos consultados.</p>}
  </details>;
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
    return params.filter(row => dimension !== 'A1' && dimension !== 'A2' && !row.technical).map((row, index) => ({ ...row, dimension, ...compareValues(row.values), domId: `scc-row-${dimension}-${index}`, key: `${selectionKey}:${dimension}:${index}` }));
  });
  return <>
    <MethodologicalSynthesis data={data} />
    <p>Las diferencias experimentales no implican incompatibilidad. “Comparables” reúne parámetros cuya comparación requiere advertencias o evidencia adicional; cada celda conserva su estado.</p>
    <PartitionCards data={data} />
    {['Con diferencias', 'Comparables', 'Sin diferencias'].map(group => {
      const shared = group === 'Sin diferencias';
      const partial = group === 'Comparables';
      const groupRows = rows.filter(row => row.group === group);
      const columns = shared ? 3 : data.selections.length + (partial ? 2 : 1);
      return <section className="scc-parameter-group" key={group}>
        <button className="ds-button" aria-expanded={groups.includes(group)} aria-controls={`scc-group-${group.replaceAll(' ', '-')}`} onClick={() => setGroups(old => old.includes(group) ? old.filter(g => g !== group) : [...old, group])}>{group} · {groupRows.length}</button>
        {groups.includes(group) && <>
          <div id={`scc-group-${group.replaceAll(' ', '-')}`} className="report-table-scroll" tabIndex={0} role="region" aria-label={`${group} A1–A6`}><table className="report-data-table scc-preflight-table scc-parameter-table" data-shared={shared}>
            <caption>{group} · parámetros de los RUN seleccionados</caption>
            <thead><tr>{shared && <th scope="col">Módulo</th>}<th scope="col" className="scc-parameter-label">Parámetro</th>{partial && <th scope="col">Estado</th>}{shared ? <th scope="col">Valor compartido</th> : data.selections.map((selection, index) => <th scope="col" key={selection.selection_id}>RUN {String.fromCharCode(65 + index)}<br /><small>{architecture(data, selection)}</small></th>)}</tr></thead>
            {(Object.keys(dimensions) as Dimension[]).map(dimension => {
              const moduleRows = groupRows.filter(row => row.dimension === dimension);
              return moduleRows.length > 0 && <tbody key={dimension}>{moduleRows.map((row, index) => <Fragment key={row.key}>
                <tr>{shared && index === 0 && <th scope="rowgroup" rowSpan={moduleRows.length + moduleRows.filter(item => item.details && expanded.includes(item.key)).length}><span className="scc-module-badge">{dimension}</span><small>{dimensions[dimension]}</small></th>}
                  <th scope="row" className="scc-parameter-label">{row.details ? <button className="ds-button" aria-expanded={expanded.includes(row.key)} aria-controls={row.domId} onClick={() => setExpanded(old => old.includes(row.key) ? old.filter(k => k !== row.key) : [...old, row.key])}>{row.dimension} · {row.label}</button> : <>{row.dimension} · {row.label}</>}{group === 'Con diferencias' && <small className="scc-impact">{row.dimension === 'A4' ? 'Configuración experimental · variable a investigar; no implica incompatibilidad.' : row.dimension === 'A3' ? 'Población y correspondencia · contextualiza los contrastes pareados.' : row.dimension === 'A5' ? 'Checkpoint · contextualiza la atribución y reproducibilidad.' : row.dimension === 'A6' ? 'Protocolo · contextualiza la interpretación de métricas.' : 'Diferencia descriptiva; impacto no determinado.'}</small>}</th>
                  {partial && <td>{row.values.some(value => value?.state === 'query_error') ? 'ERROR_DE_CONSULTA' : 'Evidencia parcial'}</td>}
                  {shared ? <td>{row.dimension === 'A6' ? <ConsolidatedDetail fields={evaluationDetails(data).slice(0, 5)} data={data} /> : <ParameterValue value={row.values[0]} />}<span className="scc-equal">{data.selections.map((_, i) => String.fromCharCode(65 + i)).join('=')}</span></td>
                    : row.dimension === 'A6' ? <td colSpan={data.selections.length}><ConsolidatedDetail fields={evaluationDetails(data).slice(0, 5)} data={data} /></td>
                      : row.values.every(value => !value || value.state === 'unknown' || (value.state === 'known' && value.value === null)) ? <td colSpan={data.selections.length}>Sin evidencia suficiente en los {data.selections.length} RUN</td>
                        : row.values.map((value, i) => <td key={data.selections[i].selection_id} data-numeric={value?.state === 'known' && typeof value.value === 'number'} data-match={row.matches[i]} data-match-tone={row.matches[i] ? [...new Set(row.matches.filter(Boolean))].indexOf(row.matches[i]) % 2 : undefined} title={row.matches[i] ? `Coinciden: ${row.matches[i]!.split('').join('=')}` : undefined}><ParameterValue value={value} />

                        </td>)}
                </tr>
                {row.details && expanded.includes(row.key) && <tr className="scc-expanded-row" id={row.domId}><td colSpan={columns - (shared ? 1 : 0)}><ConsolidatedDetail fields={row.dimension === 'A6' ? row.details.slice(5) : row.details} data={data} /></td></tr>}
              </Fragment>)}</tbody>;
            })}
          </table></div>
          {groupRows.length === 0 && <p>No hay parámetros en este grupo.</p>}
          <p className="scc-meta">{shared ? 'Valores acreditados compartidos entre los RUN seleccionados. Un consumo registrado de cero indica que no hay registros de consumo individual en la fuente consultada; no demuestra ausencia de entrenamiento.' : partial ? 'La ausencia uniforme de evidencia no discrimina entre RUN, pero limita la comparación de este parámetro. Los errores de consulta conservan su condición técnica.' : 'La época seleccionada corresponde al checkpoint, no al total ejecutado.'}</p>
        </>}
      </section>;
    })}
    <EvidenceInventory data={data} fields={[...(Object.keys(dimensions) as Dimension[]).flatMap(dimension => dimension === 'A4' ? rows.filter(row => row.dimension === dimension) : parameterRows(data, dimension)), ...evaluationDetails(data), { label: 'Disponibilidad e integridad física del checkpoint', values: data.selections.map(selection => data.checkpoints.some(check => check.selection_id === selection.selection_id) ? { state: 'not_checked' as const, reason: 'El contrato consultado no comprueba el archivo ni su SHA-256 físico.', evidence_ids: data.checkpoints.filter(check => check.selection_id === selection.selection_id).flatMap(check => check.evidence_ids) } : undefined) }]} />
    <ComparisonPython data={data} />
    <details className="ds-accordion"><summary>Detalle técnico y trazabilidad</summary><p>Consulta: {data.generated_at}</p>{data.consistency.limitations.map(limit => <p key={limit}>{limit}</p>)}
      <details id="scc-technical-registry" tabIndex={-1}><summary>Identificadores y fuentes A1–A6</summary><p>TRAIN → checkpoint → identidad EVALUATE/EXPLAIN → intento → resultados y artefactos. Cada vínculo se conserva según la fuente disponible; un intento fallido o incompleto no se presenta como verificado.</p><p>identity_hash identifica la identidad del assessment; protocol_hash identifica el protocolo; SHA-256 registrado identifica el contenido esperado del checkpoint y no acredita una comprobación física actual.</p>{data.selections.map((selection, index) => <section key={selection.selection_id}><h3>Trazabilidad técnica · RUN {String.fromCharCode(65 + index)}</h3><p>run_id · TRAIN de origen: <CompactValue value={selection.training_run_id} /></p>{(Object.keys(dimensions) as Dimension[]).map(dimension => <div key={dimension} id={evidenceTarget(selection.selection_id, dimension)} tabIndex={-1}><h4>{dimension} — {dimensions[dimension]} {data.dimensions.filter(item => item.dimension === dimension).map(item => <VerdictBadge key={item.scope.scope_id} verdict={item.verdict} />)}</h4><EvidenceCell data={data} selection={selection} dimension={dimension} /></div>)}{data.evidence.filter(ref => !(ref.source in dimensions) && ref.selection_ids.includes(selection.selection_id)).map(ref => <div key={ref.evidence_id} id={evidenceTarget(selection.selection_id, ref.evidence_id)} tabIndex={-1}><h4>{ref.source}</h4><ParameterValue value={ref.value} /><small>{ref.evidence_id} · {ref.operation} · {ref.verification} · {ref.observed_at}</small></div>)}</section>)}</details>
      <details id="scc-analysis-diagnostics" tabIndex={-1}><summary>Diagnóstico técnico por análisis</summary>
        <ConsolidatedFindings data={data} />
        <AvailabilityMatrix data={data} /></details>

    </details>
  </>;
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function CellSearch({focus, onFocus}: {focus?: string | null; onFocus: (sample: string | null) => void}) {
  const [text, setText] = useState(focus ?? '');
  const valid = UUID.test(text.trim());
  return <form className="scc-cell-search" role="search" onSubmit={event => { event.preventDefault(); if (valid) onFocus(text.trim().toLowerCase()); }}>
    <label>Buscar célula por ID<input className="ds-control" value={text} placeholder="00407b51-0603-5260-a0db-1ab700451f9f" spellCheck={false} onChange={event => setText(event.target.value)} /></label>
    <button type="submit" className="ds-button" disabled={!valid}>Mostrar célula</button>
    <small className="scc-meta">También puedes elegirla con «Explicar» en Errores y consenso.</small>
  </form>;
}

function ComparisonModules({ ids, datasource, selections, explains, canGenerate, onGenerated, revision, active, focusSample, onFocus }: { ids: string[]; datasource: string; selections: RequestedSelection[]; explains?: Record<string, string[]>; canGenerate?: boolean; onGenerated?: () => void; revision: number; active: boolean; focusSample?: string | null; onFocus: (sample: string | null) => void }) {
  const { executor, blocked } = useExplainExecutor(active && Boolean(canGenerate));
  return <section className="scc-science-module" aria-label="Explicabilidad XAI"><h3>Explicabilidad XAI</h3>
    {canGenerate && <p className="scc-executor" data-available={executor?.available ?? false} role="status">{executorLabel(executor)}{executor && !executor.available && executor.executor === 'host_gpu' && <> · Inícialo en el host: <code>{executor.start_command ?? 'scripts/host_services.sh start explain'}</code></>}</p>}
    {focusSample
      ? <div className="scc-focus" role="status"><span>Célula seleccionada: <code>{focusSample}</code></span>
          <button type="button" className="ds-button" data-size="compact" onClick={() => onFocus(null)}>Ver todas las explicaciones</button></div>
      : <CellSearch key={focusSample ?? ''} focus={focusSample} onFocus={onFocus} />}
    {ids.map((id, index) => <section key={id}><h4>RUN {String.fromCharCode(65 + index)}</h4><PersistedXAI key={JSON.stringify([selections.find(s => s.training_run_id === id), revision])} selection={selections.find(s => s.training_run_id === id) ?? { training_run_id: id }} datasource={datasource} active={active} attemptIds={explains?.[id]} canGenerate={canGenerate} blocked={blocked} onGenerated={onGenerated} focusSample={focusSample} /></section>)}
  </section>;
}

const sectionModules: Partial<Record<AnalysisSection, Module[]>> = { aprendizaje: ['curves'], desempeno: ['metrics'], errores: ['consensus'], explicabilidad: ['xai'], representaciones: ['embeddings', 'pca', 'umap', 'cka'] };
const statePriority: string[] = ['ERROR_DE_CONSULTA', 'NO_COMPARABLE', 'EVIDENCIA_INSUFICIENTE', 'COMPARABLE_CON_ADVERTENCIAS', 'COMPARABLE'];
// A section shows its least favourable analysis verdict; the full matrix stays in Trazabilidad.
export function sectionStates(data: PreflightResponse | undefined) {
  if (!data) return {};
  return Object.fromEntries(Object.entries(sectionModules).flatMap(([section, moduleIds]) => {
    const states: string[] = data.analyses.filter(analysis => moduleIds!.includes(analysis.module_id)).map(analysis => verdictText(analysis.verdict));
    const state = statePriority.find(item => states.includes(item));
    return state ? [[section, { state, label: stateLabels[state] }]] : [];
  })) as Partial<Record<AnalysisSection, { state: string; label: string }>>;
}

function AnalysisContextBar({ data, ids }: { data?: PreflightResponse; ids: string[] }) {
  const dataset = data?.selections[0] ? projectField(data, 'A1', data.selections[0].selection_id, 'name') : undefined;
  const splits = data ? [...new Set(data.selections.map(selection => selection.split.state === 'known' ? String(selection.split.value).toUpperCase() : 'Partición sin evidencia'))] : [];
  return <div className="scc-context-bar" aria-label="Contexto del análisis">
    <strong>{ids.length === 1 ? 'Qué aprendió el modelo' : 'Comparación científica'}</strong>
    {dataset?.state === 'known' && <span>{jsonText(dataset.value)}</span>}
    {splits.length > 0 && <span>{splits.join(' · ')}</span>}
    <ul className="scc-run-chips">{ids.map((id, index) => <li key={id} data-run={index}>RUN {String.fromCharCode(65 + index)}{data?.selections[index] && <small>{architecture(data, data.selections[index])}</small>}</li>)}</ul>
  </div>;
}

function SectionMap({ states, onSelect }: { states: ReturnType<typeof sectionStates>; onSelect: (section: AnalysisSection) => void }) {
  return <nav className="scc-section-map" aria-label="Mapa del análisis">{analysisSections.filter(item => item.id !== 'resumen').map(item => <button key={item.id} type="button" className="scc-section-card" onClick={() => onSelect(item.id)}>
    <strong>{item.label}</strong><span>{item.question}</span>{states[item.id] && <span className="scc-verdict" data-state={states[item.id]!.state}>{states[item.id]!.label}</span>}
  </button>)}</nav>;
}

type SectionProps = { section?: AnalysisSection; onSectionChange?: (section: AnalysisSection) => void; explains?: Record<string, string[]>; canGenerate?: boolean; onGenerated?: () => void;
  focusSample?: string | null; onFocusSample?: (sample: string | null, section?: AnalysisSection) => void };
function ComparisonEvidenceSession({ ids, datasource, maximum, selections, section: requested, onSectionChange, explains, canGenerate, onGenerated, focusSample: requestedFocus, onFocusSample }: { ids: string[]; datasource: string; maximum?: number; selections: RequestedSelection[] } & SectionProps) {
  const cache = useMemo(createComparisonCache, []);
  const [revision, setRevision] = useState(0);
  const [xaiRevision, setXaiRevision] = useState(0);
  const [localSection, setLocalSection] = useState<AnalysisSection>(defaultAnalysisSection);
  const section = requested ?? localSection;
  const select = (next: AnalysisSection) => { setLocalSection(next); onSectionChange?.(next); };
  const [localFocus, setLocalFocus] = useState<string | null>(null);
  const focusSample = requestedFocus !== undefined ? requestedFocus : localFocus;
  // Choosing a cell (Errores «Explicar» or the search) opens Explicabilidad on it in one step.
  const focus = (sample: string | null, next?: AnalysisSection) => {
    setLocalFocus(sample);
    if (onFocusSample) onFocusSample(sample, next); else if (next) select(next);
  };
  const visited = useVisitedSections(section);
  const key = maximum !== undefined && ids.length >= 2 && ids.length <= maximum ? JSON.stringify(['preflight', datasource, selections, revision]) : null;
  const { data, error, loading } = useComparisonEvidence(cache, key, () => api.getComparisonPreflight(datasource, { selections }));
  const refresh = () => { cache.clear(); setRevision(value => value + 1); setXaiRevision(value => value + 1); };
  const findings = data ? [...new Map([...data.dimensions.flatMap(item => item.findings), ...data.analyses.flatMap(item => item.findings)].map(item => [item.reason_id, item])).values()] : [];
  const states = sectionStates(data);
  const moduleProps = { cache, datasource, selections, evidenceRevision: revision };
  return <>
    <div className="scc-sticky-head">
      {ids.length > 0 && <AnalysisContextBar data={data} ids={ids} />}
      <AnalysisSectionNav section={section} onSelect={select} states={states} />
    </div>
    <AnalysisPanel id="resumen" section={section} visited={visited}><>
      <section className="report-section" aria-label="Resumen metodológico" aria-busy={loading}>
        <div className="ds-page-header"><h3>Resumen metodológico</h3><button className="ds-button" onClick={refresh}>Actualizar evidencia</button></div>
        {!key && <p>{ids.length === 1 ? 'RUN individual seleccionado: sus resultados están disponibles en cada sección; el preflight comparativo requiere al menos dos TRAIN.' : 'Selecciona entre dos TRAIN y el máximo configurado para consultar el Preflight.'}</p>}
        {loading && <p role="status">Consultando Preflight…</p>}
        {error ? <ErrorMessage error={error} retry={refresh} /> : null}
        {data && <>
          <p className="scc-meta">{data.evidence.length} referencias</p>
          <p>{data.selections.length} TRAIN participantes · {data.selections.map(selection => architecture(data, selection)).join(' / ')}</p>
          <MethodologicalWarnings data={data} findings={findings} />
          {data.technical_errors.map(item => <p role="alert" key={item.error_id}>ERROR_DE_CONSULTA · {item.message} · {item.operation} · {item.error_id}</p>)}
        </>}
      </section>
      {ids.length > 0 && <SectionMap states={states} onSelect={select} />}
      {ids.length > 0 && <ScientificQuestions {...moduleProps} active={section === 'resumen'} />}
    </></AnalysisPanel>
    <AnalysisPanel id="aprendizaje" section={section} visited={visited}><CurvesModule {...moduleProps} active={section === 'aprendizaje'} /></AnalysisPanel>
    <AnalysisPanel id="desempeno" section={section} visited={visited}><MetricsModule {...moduleProps} active={section === 'desempeno'} /></AnalysisPanel>
    <AnalysisPanel id="errores" section={section} visited={visited}><ConsensusModule {...moduleProps} active={section === 'errores'} onExplain={sample => focus(sample, 'explicabilidad')} /></AnalysisPanel>
    <AnalysisPanel id="explicabilidad" section={section} visited={visited}><ComparisonModules selections={selections} explains={explains} canGenerate={canGenerate} onGenerated={onGenerated} revision={xaiRevision} ids={ids} datasource={datasource} active={section === 'explicabilidad'} focusSample={focusSample} onFocus={sample => focus(sample)} /></AnalysisPanel>
    <AnalysisPanel id="representaciones" section={section} visited={visited}><ScientificRepresentations {...moduleProps} canGenerate={canGenerate} active={section === 'representaciones'} /></AnalysisPanel>
    <AnalysisPanel id="trazabilidad" section={section} visited={visited}>{data ? <PreflightEvidence data={data} /> : <p>{ids.length === 1 ? 'RUN individual seleccionado. Sus resultados permanecen disponibles; el preflight comparativo requiere al menos dos TRAIN.' : 'El detalle utiliza la misma consulta del resumen metodológico.'}</p>}</AnalysisPanel>
  </>;
}

export function ScientificPreflight(props: { ids: string[]; datasource: string; maximum?: number; selections: RequestedSelection[] } & SectionProps) {
  const { user, status } = useAuth();
  // Remount all retained evidence on a change of user, permissions, datasource or TRAIN set.
  const scope = JSON.stringify([user, status, props.datasource, props.ids]);
  return <Fragment key={scope}><ComparisonEvidenceSession {...props} canGenerate={Boolean(user?.permissions?.includes('scientific.cell_classification.explain'))} /></Fragment>;
}
