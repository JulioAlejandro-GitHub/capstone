import type { JsonValue, Observation, PreflightResponse } from '../../types/scientificPreflight';
import { datasetCheckLabel } from '../../utils/datasetChecks';
import { projectField, stableValue } from '../../utils/preflightPresentation';

const number = new Intl.NumberFormat('es-CL', { maximumSignificantDigits: 21 });
function record(value: JsonValue): Record<string, JsonValue> | undefined {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : undefined;
}
function checkState(value: JsonValue | undefined) {
  if (value === 'PASS') return { category: 'passed', label: 'PASS', tone: 'approved', icon: '✓' };
  if (value === 'FAIL') return { category: 'failed', label: 'FAIL', tone: 'rejected', icon: '✕' };
  if (value === 'WARNING') return { category: 'warning', label: 'WARNING', tone: 'warning', icon: '!' };
  if (value == null || value === '') return { category: 'missing', label: value === undefined ? 'Sin evidencia · campo ausente' : value === null ? 'Sin evidencia · nulo' : 'Sin evidencia · vacío', tone: 'neutral', icon: 'ⓘ' };
  return { category: 'unknown', label: typeof value === 'string' ? value : JSON.stringify(value), tone: 'neutral', icon: '?' };
}
function CheckValue({ value, name }: { value: JsonValue | undefined; name: string }) {
  if (value === undefined) return <span>Campo ausente</span>;
  if (value === null) return <span>Nulo</span>;
  if (typeof value === 'number') return <span>{number.format(value)}</span>;
  if (typeof value === 'boolean') return <span>{value ? 'true' : 'false'}</span>;
  if (typeof value === 'object') return <details><summary>{Array.isArray(value) ? `Arreglo · ${value.length} elementos` : `Objeto · ${Object.keys(value).length} campos`}</summary><pre className="scc-integrity-value" tabIndex={0}>{JSON.stringify(value, null, 2)}</pre></details>;
  // Only these check/value combinations have documented semantics in formal_validation.
  const label = /^class_presence_(train|val|test)$/.test(name) && value === 'both' ? 'Ambas'
    : name === 'split_completeness' && value === 'complete' ? 'Completo' : value;
  if (value.length > 80) return <details><summary>Texto · {value.length} caracteres</summary><pre className="scc-integrity-value" tabIndex={0}>{value}</pre></details>;
  return <span title={value}>{label === '' ? 'Cadena vacía' : label}</span>;
}
function Checks({ observation, runs }: { observation: Observation | undefined; runs: string[] }) {
  const heading = <><h4>Integridad del dataset</h4><p className="scc-meta">{runs.join(', ')}</p></>;
  if (observation?.state !== 'known') return <>{heading}<p role={observation?.state === 'query_error' ? 'alert' : undefined}>
    {observation?.state === 'query_error' ? `ERROR_DE_CONSULTA · ${observation.error_ids.join(', ')}` : observation ? `${observation.state === 'not_applicable' ? 'No aplicable' : observation.state === 'not_checked' ? 'No verificado' : 'Sin evidencia'} · ${observation.reason}` : 'Sin evidencia de comprobaciones en la respuesta consultada.'}
  </p></>;
  if (!Array.isArray(observation.value)) return <>{heading}<p>Formato de comprobaciones no reconocido; no se puede determinar el total.</p><CheckValue value={observation.value} name="" /></>;
  const checks = observation.value;
  const counts = { passed: 0, failed: 0, missing: 0, warning: 0, unknown: 0 };
  for (const check of checks) counts[checkState(record(check)?.status).category as keyof typeof counts]++;
  const allPassed = checks.length > 0 && counts.passed === checks.length;
  return <>
    <div className="ds-page-header"><h4>Integridad del dataset</h4><span className="ds-status" data-tone={allPassed ? 'approved' : counts.failed ? 'rejected' : 'neutral'}>{counts.passed}/{checks.length} PASS{!allPassed && checks.length > 0 ? ' · controles sin PASS' : ''}</span></div>
    <p className="scc-meta">{runs.join(', ')} · Número de verificaciones: {checks.length}</p>
    <dl className="scc-integrity-counts">
      <div className="ds-status" data-tone="approved"><dt>Aprobadas</dt><dd>{counts.passed}</dd></div>
      <div className="ds-status" data-tone="rejected"><dt>Fallidas</dt><dd>{counts.failed}</dd></div>
      <div className="ds-status" data-tone="neutral"><dt>Sin evidencia</dt><dd>{counts.missing}</dd></div>
      {counts.warning > 0 && <div className="ds-status" data-tone="warning"><dt>Advertencias</dt><dd>{counts.warning}</dd></div>}
      {counts.unknown > 0 && <div className="ds-status" data-tone="neutral"><dt>No clasificados</dt><dd>{counts.unknown}</dd></div>}
    </dl>
    <p>{!checks.length ? 'No hay comprobaciones registradas en la lista consultada.' : allPassed ? `Las ${checks.length} comprobaciones registradas del split tienen estado PASS.` : `${checks.length} controles registrados: ${counts.passed} PASS, ${counts.failed} FAIL, ${counts.missing} sin evidencia de estado, ${counts.warning} WARNING y ${counts.unknown} no clasificados.`}</p>
    <details className="ds-accordion"><summary>Comprobaciones registradas <span className="scc-meta">{checks.length} controles</span></summary>
      {checks.length > 0 && <div className="report-table-scroll" role="region" aria-label="Comprobaciones de integridad del dataset" tabIndex={0}><table className="report-data-table scc-integrity-table">
        <thead><tr><th scope="col">Comprobación</th><th scope="col">Observado</th><th scope="col">Esperado</th><th scope="col">Estado</th></tr></thead>
        <tbody>{checks.map((check, index) => {
          const item = record(check);
          const name = typeof item?.check_name === 'string' ? item.check_name : '';
          const state = checkState(item?.status);
          return <tr key={index}><th scope="row"><span title={name || undefined} aria-label={name ? `${datasetCheckLabel(name)} · ${name}` : undefined}>{name ? datasetCheckLabel(name) : 'Comprobación sin nombre acreditado'}</span>
            {(!item || (item.check_name != null && typeof item.check_name !== 'string') || Object.keys(item).some(key => !['check_name', 'status', 'observed_value', 'expected_value'].includes(key))) && <CheckValue value={check} name="" />}</th>
            <td data-numeric={typeof item?.observed_value === 'number'}><CheckValue value={item?.observed_value} name={name} /></td>
            <td data-numeric={typeof item?.expected_value === 'number'}><CheckValue value={item?.expected_value} name={name} /></td>
            <td><span className="ds-status" data-tone={state.tone}><span aria-hidden="true">{state.icon}</span>{state.category === 'unknown' ? <CheckValue value={item?.status} name="" /> : state.label}</span></td></tr>;
        })}</tbody>
      </table></div>}
    </details>
  </>;
}

export function DatasetIntegrity({ data }: { data: PreflightResponse }) {
  const groups = new Map<string, { runs: string[]; observation: Observation | undefined }>();
  data.selections.forEach((selection, index) => {
    const observation = projectField(data, 'A2', selection.selection_id, 'checks');
    // Share a table only when dataset identity and the ordered checks are both known and equal.
    const key = selection.dataset_version_id.state === 'known' && typeof selection.dataset_version_id.value === 'string' && selection.dataset_version_id.value.length > 0 && observation?.state === 'known'
      ? stableValue([selection.dataset_version_id.value, observation.value]) : selection.selection_id;
    const group = groups.get(key);
    const run = `RUN ${String.fromCharCode(65 + index)}`;
    if (group) group.runs.push(run); else groups.set(key, { runs: [run], observation });
  });
  return <section className="ds-section scc-integrity">
    {[...groups].map(([key, group]) => <div key={key}><Checks observation={group.observation} runs={group.runs} /></div>)}
    {!groups.size && <><h4>Integridad del dataset</h4><p>Sin RUNs seleccionados.</p></>}
    <p className="scc-meta">Estos resultados acreditan los controles registrados del split; no equivalen a una verificación completa de todos los archivos y procesos posteriores.</p>
  </section>;
}
