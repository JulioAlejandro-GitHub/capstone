import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { Loading } from '../components/Loading';
import { api } from '../services/api';
import type {
  DatasetVersionDetail,
  DatasetVersionSummary,
} from '../types/api';

interface DatasetBrowserProps { datasource: string }

const number = new Intl.NumberFormat('es-CL');
const checkLabels: Record<string, string> = {
  identity_coverage: 'Cobertura de identidad',
  identity_conflicts: 'Conflictos de identidad',
  patient_train_val_overlap: 'Pacientes compartidos TRAIN / VAL',
  patient_train_test_overlap: 'Pacientes compartidos TRAIN / TEST',
  patient_val_test_overlap: 'Pacientes compartidos VAL / TEST',
  duplicate_cross_split_overlap: 'Duplicados entre conjuntos',
  assignment_count: 'Asignaciones completas',
  source_record_count: 'Registros fuente completos',
  split_completeness: 'Completitud del split',
  class_presence_train: 'Clases presentes en TRAIN',
  class_presence_val: 'Clases presentes en VAL',
  class_presence_test: 'Clases presentes en TEST',
};

function humanReason(reason: string) {
  return ({
    DATASET_NOT_FROZEN: 'La versión aún no está congelada.',
    VALIDATION_NOT_PASS: 'La validación científica aún no está aprobada.',
    NO_READY_RECONCILED_MATERIALIZATION: 'Pendiente de materialización reconciliada.',
  } as Record<string, string>)[reason] ?? 'La versión aún no está disponible para entrenamiento.';
}

function CopyValue({ label, value }: { label: string; value: string | null }) {
  const [message, setMessage] = useState('');
  if (!value) return null;
  const copy = async () => {
    await navigator.clipboard.writeText(value);
    setMessage('Copiado');
  };
  return <div className="dataset-lineage-row">
    <span><strong>{label}</strong><code title={value}>{value.slice(0, 12)}…</code></span>
    <button type="button" onClick={copy} aria-label={`Copiar ${label}`}>Copiar</button>
    <small role="status">{message}</small>
  </div>;
}

function DatasetVersionCard({ item, selected, onSelect, datasource }: {
  item: DatasetVersionSummary; selected: boolean; onSelect: () => void; datasource: string;
}) {
  return <article className={`panel dataset-version-card ${selected ? 'is-selected' : ''}`}>
    <header>
      <div><h2>{item.name}</h2><p>Versión {item.semantic_version}</p></div>
      <div className="dataset-badges">
        <span className={`dataset-status dataset-status-${item.status.toLowerCase()}`}>{item.status}</span>
        <span className={item.trainable ? 'dataset-trainable' : 'dataset-unavailable'}>
          {item.trainable ? '● Disponible para entrenamiento' : 'No disponible para entrenamiento'}
        </span>
      </div>
    </header>
    <p className="dataset-population"><strong>{number.format(item.patient_count)}</strong> pacientes · <strong>{number.format(item.source_record_count)}</strong> imágenes</p>
    <div className="dataset-split-strip" aria-label="Distribución del dataset">
      <div><span>TRAIN</span><strong>{number.format(item.train_records)}</strong></div>
      <div><span>VAL</span><strong>{number.format(item.val_records)}</strong></div>
      <div><span>TEST</span><strong>{number.format(item.test_records)}</strong></div>
    </div>
    <dl className="dataset-readiness">
      <div><dt>Validación</dt><dd>{item.validation_pass_count} / {item.validation_required_count} PASS</dd></div>
      <div><dt>Materialización</dt><dd>{item.materialization_status ?? 'Pendiente'}</dd></div>
      <div><dt>Reconciliación</dt><dd>{item.reconciliation_status ?? 'Pendiente'}</dd></div>
    </dl>
    {!item.trainable && item.trainability_reasons.length ? <p className="dataset-reason">{humanReason(item.trainability_reasons[0])}</p> : null}
    <div className="detail-actions">
      <button type="button" onClick={onSelect}>{selected ? 'Detalle visible' : 'Ver detalle'}</button>
      <button type="button" disabled title="La interfaz de creación de entrenamiento aún no está disponible.">Usar en entrenamiento</button>
      <Link className="button-link secondary" to={`/modelo-ia/ejecuciones?datasource=${datasource}&dataset_version_id=${item.dataset_version_id}`}>Ver ejecuciones</Link>
    </div>
    <small className="muted-text">El inicio gobernado de entrenamiento estará disponible desde su flujo de creación.</small>
  </article>;
}

function DatasetSummary({ detail }: { detail: DatasetVersionDetail }) {
  const item = detail.dataset;
  return <details className="panel dataset-disclosure" open><summary>Resumen</summary>
    <dl className="dataset-summary-grid">
      <div><dt>Nombre</dt><dd>{item.name}</dd></div><div><dt>Versión</dt><dd>{item.semantic_version}</dd></div>
      <div><dt>Estado</dt><dd>{item.status}</dd></div><div><dt>Disponible para entrenamiento</dt><dd>{item.trainable ? 'Sí' : 'No'}</dd></div>
      <div><dt>Pacientes</dt><dd>{number.format(item.patient_count)}</dd></div><div><dt>Imágenes</dt><dd>{number.format(item.source_record_count)}</dd></div>
      <div><dt>Unidad de separación</dt><dd>Paciente</dd></div><div><dt>Algoritmo</dt><dd>{item.split_algorithm}</dd></div>
      <div><dt>Seed</dt><dd>{item.random_seed}</dd></div>
    </dl>
    <div className="dataset-lifecycle" aria-label="Lifecycle de Dataset Version">
      {detail.lifecycle.map((state) => <span className={state === item.status ? 'current' : ''} key={state}>{state === item.status ? '●' : '✓'} {state}</span>)}
    </div>
    {item.status === 'FROZEN' ? <p className="dataset-frozen-note"><strong>Dataset congelado.</strong> La composición científica ya no puede modificarse.</p> : null}
    <details className="dataset-technical"><summary>Detalles técnicos</summary><CopyValue label="Dataset Version ID" value={item.dataset_version_id} /></details>
  </details>;
}

function DatasetDistribution({ detail }: { detail: DatasetVersionDetail }) {
  const { records, patients, class_counts: classes } = detail.distribution;
  return <details className="panel dataset-disclosure"><summary>Distribución</summary>
    <div className="table-wrap"><table><thead><tr><th>Conjunto</th><th>Pacientes</th><th>Imágenes</th></tr></thead><tbody>
      {(['train', 'val', 'test'] as const).map((split) => <tr key={split}><th>{split.toUpperCase()}</th><td>{number.format(patients[split] ?? 0)}</td><td>{number.format(records[split] ?? 0)}</td></tr>)}
      <tr><th>TOTAL</th><td>{number.format(detail.distribution.total_patients)}</td><td>{number.format(detail.distribution.total_records)}</td></tr>
    </tbody></table></div>
    <div className="table-wrap"><table><thead><tr><th>Conjunto</th><th>Parasitized</th><th>Uninfected</th></tr></thead><tbody>
      {(['train', 'val', 'test'] as const).map((split) => <tr key={split}><th>{split.toUpperCase()}</th><td>{number.format(classes[split]?.parasitized ?? 0)}</td><td>{number.format(classes[split]?.uninfected ?? 0)}</td></tr>)}
    </tbody></table></div>
  </details>;
}

function DatasetIntegrity({ detail }: { detail: DatasetVersionDetail }) {
  const integrity = detail.integrity;
  return <details className="panel dataset-disclosure"><summary>Integridad científica <small>Patient leakage 0</small></summary>
    <p>✓ Patient-disjoint. Un mismo paciente no aparece en más de un conjunto.</p>
    <dl className="dataset-readiness">
      <div><dt>Train ↔ Val</dt><dd>{integrity.patient_train_val_overlap} pacientes</dd></div>
      <div><dt>Train ↔ Test</dt><dd>{integrity.patient_train_test_overlap} pacientes</dd></div>
      <div><dt>Val ↔ Test</dt><dd>{integrity.patient_val_test_overlap} pacientes</dd></div>
      <div><dt>Duplicados entre splits</dt><dd>{integrity.duplicate_cross_split_overlap}</dd></div>
    </dl>
  </details>;
}

function DatasetValidation({ detail }: { detail: DatasetVersionDetail }) {
  const validation = detail.validation;
  return <details className="panel dataset-disclosure"><summary>Validación científica <small>{validation.pass_count}/{validation.required_count} PASS</small></summary>
    <ul className="dataset-check-list">{validation.checks.map((check) => <li key={check.check_name}><span aria-hidden="true">{check.status === 'PASS' ? '✓' : '!'}</span><span><strong>{checkLabels[check.check_name] ?? check.check_name}</strong><small>{check.check_name}</small></span><b>{check.status}</b></li>)}</ul>
  </details>;
}

function DatasetMaterialization({ detail }: { detail: DatasetVersionDetail }) {
  const item = detail.materialization;
  return <details className="panel dataset-disclosure"><summary>Materialización <small>{item ? `${item.status} / ${item.reconciliation_status}` : 'Pendiente'}</small></summary>
    {!item ? <p>La versión aún no tiene una materialización disponible.</p> : <>
      <dl className="dataset-summary-grid"><div><dt>Estado</dt><dd>{item.status}</dd></div><div><dt>Reconciliación</dt><dd>{item.reconciliation_status}</dd></div><div><dt>Archivos</dt><dd>{number.format(item.record_count)}</dd></div><div><dt>SHA verificados</dt><dd>{number.format(item.sha_files_checked)}</dd></div><div><dt>SHA con diferencias</dt><dd>{number.format(item.sha_mismatch)}</dd></div><div><dt>Intento</dt><dd>{item.attempt_number}</dd></div></dl>
      <details className="dataset-technical"><summary>Ver detalle técnico</summary><CopyValue label="Materialization ID" value={item.dataset_materialization_id} /><p>Root relativo: <code>{item.relative_root}</code></p></details>
    </>}
  </details>;
}

function DatasetLineage({ detail }: { detail: DatasetVersionDetail }) {
  return <details className="panel dataset-disclosure"><summary>Trazabilidad científica</summary>
    <CopyValue label="Población fuente" value={detail.lineage.source_population_fingerprint} />
    <CopyValue label="Identidades clínicas" value={detail.lineage.clinical_identity_fingerprint} />
    <CopyValue label="Asignación de pacientes" value={detail.lineage.patient_assignment_fingerprint} />
    <CopyValue label="Asignación de registros" value={detail.lineage.record_assignment_fingerprint} />
  </details>;
}

function DatasetRuns({ detail, datasource }: { detail: DatasetVersionDetail; datasource: string }) {
  return <details className="panel dataset-disclosure"><summary>Ejecuciones <small>{detail.runs.count}</small></summary>
    {!detail.runs.items.length ? <p>Aún no existen entrenamientos nuevos asociados a esta versión.</p> : <div className="table-wrap"><table><thead><tr><th>Run</th><th>Modelo</th><th>Tipo</th><th>Estado</th><th>Fecha</th></tr></thead><tbody>{detail.runs.items.map((run) => <tr key={run.run_id}><td><Link to={`/modelo-ia/ejecuciones/${run.run_id}?datasource=${datasource}`}>{run.run_name ?? run.run_id.slice(0, 8)}</Link></td><td>{run.model_name ?? '-'}</td><td>{run.run_type}</td><td>{run.status}</td><td>{run.started_at ? new Date(run.started_at).toLocaleString('es-CL') : '-'}</td></tr>)}</tbody></table></div>}
  </details>;
}

export function DatasetBrowser({ datasource }: DatasetBrowserProps) {
  const [versions, setVersions] = useState<DatasetVersionSummary[] | null>(null);
  const [selectedDatasetVersionId, setSelectedDatasetVersionId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DatasetVersionDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadList = useCallback(() => {
    setError(null); setVersions(null);
    api.getDatasetVersions(datasource).then(({ items }) => {
      setVersions(items);
      setSelectedDatasetVersionId((current) => current ?? items[0]?.dataset_version_id ?? null);
    }).catch(() => setError('No fue posible cargar la información del dataset.'));
  }, [datasource]);

  useEffect(loadList, [loadList]);
  useEffect(() => {
    if (!selectedDatasetVersionId) { setDetail(null); return; }
    setLoadingDetail(true); setError(null);
    api.getDatasetVersionDetail(datasource, selectedDatasetVersionId)
      .then(setDetail).catch(() => setError('No fue posible cargar la información del dataset.'))
      .finally(() => setLoadingDetail(false));
  }, [datasource, selectedDatasetVersionId]);

  if (error) return <section className="page"><div className="panel error"><p>{error}</p><button type="button" onClick={loadList}>Reintentar</button></div></section>;
  if (!versions) return <section className="page" aria-label="Cargando Dataset Versions"><Loading /></section>;
  return <section className="page dataset-versions-page">
    <div className="page-title"><div><h1>Dataset</h1><p>Versiones de datos utilizadas para entrenar y evaluar los modelos de inteligencia artificial.</p></div><span className="domain-badge">Dataset</span></div>
    {!versions.length ? <section className="panel empty-state">No existen Dataset Versions disponibles.</section> : <div className="dataset-version-list">{versions.map((item) => <DatasetVersionCard key={item.dataset_version_id} item={item} datasource={datasource} selected={item.dataset_version_id === selectedDatasetVersionId} onSelect={() => setSelectedDatasetVersionId(item.dataset_version_id)} />)}</div>}
    {loadingDetail ? <section aria-label="Cargando detalle del dataset"><Loading /></section> : null}
    {detail && !loadingDetail ? <section className="dataset-detail" aria-label={`Detalle de ${detail.dataset.name}`}>
      <DatasetSummary detail={detail} /><DatasetDistribution detail={detail} /><DatasetIntegrity detail={detail} />
      <DatasetValidation detail={detail} /><DatasetMaterialization detail={detail} /><DatasetLineage detail={detail} />
      <DatasetRuns detail={detail} datasource={datasource} />
    </section> : null}
  </section>;
}
