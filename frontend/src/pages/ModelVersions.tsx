import { useEffect, useMemo, useState } from 'react';
import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type { DeploymentRow, ModelVersionLineageRow, ModelVersionRow } from '../types/api';
import { formatDate, formatMetric } from '../utils/format';

const short = (value: string | null | undefined, size = 8) => (value ? `${value.slice(0, size)}…` : '—');

interface ModelVersionsProps {
  datasource: string;
  onRunSelect: (id: string) => void;
  onDeployments: () => void;
  selectedModelVersionId?: string | null;
}

export function ModelVersions({ datasource, onRunSelect, onDeployments, selectedModelVersionId }: ModelVersionsProps) {
  const [rows, setRows] = useState<ModelVersionRow[]>([]);
  const [deployments, setDeployments] = useState<DeploymentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState('');
  const [status, setStatus] = useState('');
  const [lineage, setLineage] = useState('');
  const [selected, setSelected] = useState<ModelVersionRow | null>(null);
  const [lineageRows, setLineageRows] = useState<ModelVersionLineageRow[]>([]);

  // Estado del Modal de Despliegue
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [deployEnv, setDeployEnv] = useState('staging');
  const [deployAlias, setDeployAlias] = useState('champion');
  const [deployName, setDeployName] = useState('');
  const [deployReason, setDeployReason] = useState('');
  const [deploying, setDeploying] = useState(false);
  const [deployError, setDeployError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([api.getModelVersions(datasource), api.getDeployments(datasource, true)])
      .then(([versions, active]) => {
        setRows(versions.items);
        setDeployments(active.items);
        if (selectedModelVersionId) {
          const match = versions.items.find((item) => item.id === selectedModelVersionId);
          if (match) {
            setSelected(match);
            api.getModelVersionLineage(datasource, match.id).then((res) => setLineageRows(res.items)).catch(() => setLineageRows([]));
          }
        }
      })
      .catch((reason) => setError(String(reason)))
      .finally(() => setLoading(false));
  }, [datasource, selectedModelVersionId]);

  const filtered = useMemo(
    () => rows.filter((row) => (!model || row.model_name === model) && (!status || row.status === status) && (!lineage || row.lineage_status === lineage)),
    [rows, model, status, lineage],
  );

  const open = (row: ModelVersionRow) => {
    setSelected(row);
    api.getModelVersionLineage(datasource, row.id).then((result) => setLineageRows(result.items)).catch(() => setLineageRows([]));
  };

  const handleOpenDeployModal = (row: ModelVersionRow) => {
    setSelected(row);
    setDeployName(`${row.model_name}_deployment`);
    setDeployEnv('staging');
    setDeployAlias('champion');
    setDeployReason('');
    setDeployError(null);
    setShowDeployModal(true);
  };

  const handleCreateDeployment = async () => {
    if (!selected) return;
    setDeploying(true);
    setDeployError(null);
    try {
      const url = new URL('/api/deployments', import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000');
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_version_id: selected.id,
          deployment_name: deployName || `${selected.model_name}_deployment`,
          environment: deployEnv,
          alias: deployAlias,
          threshold_profile_id: selected.evaluation_run_id || selected.id,
          deployed_by: 'ui_user',
          metadata: { deployment_reason: deployReason },
          activate: false,
          dry_run: false,
        }),
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text);
      }
      setShowDeployModal(false);
      onDeployments();
    } catch (err) {
      setDeployError(err instanceof Error ? err.message : 'Error al crear el despliegue');
    } finally {
      setDeploying(false);
    }
  };

  if (loading) return <div className="page"><Loading /></div>;
  if (error) return <div className="page"><div className="panel warning-panel"><h1>No se pudieron cargar los modelos liberados</h1><p>{error}</p></div></div>;

  const models = [...new Set(rows.map((row) => row.model_name))];
  const statuses = [...new Set(rows.map((row) => row.status))];
  const lineages = [...new Set(rows.map((row) => row.lineage_status))];

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Modelos liberados</h1>
          <p>Versiones inmutables, su evaluación y estado operativo.</p>
        </div>
      </div>
      <div className="panel filter-bar">
        <label>Modelo
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            <option value="">Todos</option>
            {models.map((x) => <option key={x}>{x}</option>)}
          </select>
        </label>
        <label>Estado
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todos</option>
            {statuses.map((x) => <option key={x}>{x}</option>)}
          </select>
        </label>
        <label>Linaje
          <select value={lineage} onChange={(e) => setLineage(e.target.value)}>
            <option value="">Todos</option>
            {lineages.map((x) => <option key={x}>{x}</option>)}
          </select>
        </label>
      </div>

      <div className="panel">
        <DataTable
          rows={filtered}
          emptyText="No hay model versions para los filtros seleccionados."
          getRowKey={(row) => row.id}
          columns={[
            { header: 'Modelo / versión', render: (row) => <><strong>{row.model_name}</strong><br /><small>v{row.version_number ?? '—'} · {short(row.id)}</small></> },
            { header: 'Estado', render: (row) => <><StatusBadge status={row.status} /><br /><small>{row.lineage_status}</small></> },
            { header: 'Training', render: (row) => <code>{short(row.training_run_id)}</code> },
            { header: 'SHA-256', render: (row) => <code>{short(row.artifact_sha256, 12)}</code> },
            { header: 'Evaluación', render: (row) => <><span>Recall {formatMetric(row.recall_parasitized)}</span><br /><span>Spec. {formatMetric(row.specificity)}</span><br /><span>F2 {formatMetric(row.f2_parasitized)}</span></> },
            { header: 'Threshold', render: (row) => formatMetric(row.threshold_used) },
            { header: 'Creado', render: (row) => formatDate(row.created_at) },
            {
              header: 'Operación',
              render: (row) => {
                const active = deployments.find((item) => item.model_version_id === row.id);
                return active ? <span>{active.alias}<br /><small>{active.environment}</small></span> : 'Sin deployment activo';
              },
            },
            {
              header: 'Acciones',
              render: (row) => (
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button type="button" className="table-action" onClick={() => open(row)}>Detalle</button>
                  <button type="button" className="table-action" style={{ backgroundColor: '#0284c7', color: '#fff' }} onClick={() => handleOpenDeployModal(row)}>Desplegar</button>
                </div>
              ),
            },
          ]}
        />
      </div>

      {selected ? (
        <div className="panel detail-panel">
          <div className="section-heading">
            <h2>{selected.model_name} · v{selected.version_number ?? '—'}</h2>
            <button type="button" onClick={() => setSelected(null)}>Cerrar</button>
          </div>
          <div className="facts-grid">
            <span>Model version<strong>{selected.id}</strong></span>
            <span>Training run<strong>{selected.training_run_id}</strong></span>
            <span>Linaje<strong>{selected.lineage_status}</strong></span>
            <span>Explicabilidad<strong>{selected.explainability_available ? 'Disponible' : 'No registrada'}</strong></span>
          </div>
          <h3>Linaje</h3>
          {lineageRows.length ? (
            <ol className="lineage-list">
              {lineageRows.map((item) => (
                <li key={item.id}>
                  <strong>{item.relationship_type}</strong>
                  <code>{short(item.child_run_id, 12)}</code>
                  {item.relationship_type.includes('evaluates') ? (
                    <button type="button" onClick={() => onRunSelect(item.child_run_id)}>Ver evaluación</button>
                  ) : null}
                </li>
              ))}
            </ol>
          ) : (
            <p className="empty-state">Sin relaciones registradas.</p>
          )}
          <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
            <button type="button" className="table-action" onClick={onDeployments}>Ver deployments</button>
            <button type="button" className="table-action" style={{ backgroundColor: '#0284c7', color: '#fff' }} onClick={() => handleOpenDeployModal(selected)}>Desplegar versión</button>
          </div>
        </div>
      ) : null}

      {/* Modal de Despliegue */}
      {showDeployModal && selected ? (
        <div style={{ position: 'fixed', inset: 0, zIndex: 100, backgroundColor: 'rgba(0, 0, 0, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '8px', maxWidth: '480px', width: '100%', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}>
            <h2 style={{ margin: '0 0 12px 0', fontSize: '18px' }}>Solicitar Despliegue de Modelo</h2>
            <p style={{ fontSize: '13px', color: '#475569', margin: '0 0 16px 0' }}>
              Creación de una instancia de despliegue para la versión <strong>{selected.model_name}</strong> (v{selected.version_number ?? '1'}).
            </p>

            {deployEnv === 'production' ? (
              <div style={{ padding: '10px 12px', backgroundColor: '#fffbebfb', border: '1px solid #fcd34d', borderRadius: '6px', fontSize: '12px', color: '#92400e', marginBottom: '14px' }}>
                ⚠️ <strong>Confirmación de Producción:</strong> Se activará una versión para el ambiente de producción. La activación final se realizará desde Despliegues.
              </div>
            ) : null}

            <form style={{ display: 'flex', flexDirection: 'column', gap: '12px' }} onSubmit={(e) => { e.preventDefault(); handleCreateDeployment(); }}>
              <label style={{ fontSize: '12px', fontWeight: 600 }}>Entorno
                <select value={deployEnv} onChange={(e) => setDeployEnv(e.target.value)} style={{ width: '100%', padding: '6px', marginTop: '4px' }}>
                  <option value="experimental">Experimental</option>
                  <option value="staging">Staging</option>
                  <option value="production">Producción</option>
                </select>
              </label>

              <label style={{ fontSize: '12px', fontWeight: 600 }}>Nombre del Despliegue
                <input type="text" value={deployName} onChange={(e) => setDeployName(e.target.value)} style={{ width: '100%', padding: '6px', marginTop: '4px' }} required />
              </label>

              <label style={{ fontSize: '12px', fontWeight: 600 }}>Alias
                <select value={deployAlias} onChange={(e) => setDeployAlias(e.target.value)} style={{ width: '100%', padding: '6px', marginTop: '4px' }}>
                  <option value="champion">Champion</option>
                  <option value="candidate">Candidate</option>
                </select>
              </label>

              <label style={{ fontSize: '12px', fontWeight: 600 }}>Motivo o Comentario
                <textarea value={deployReason} onChange={(e) => setDeployReason(e.target.value)} placeholder="Motivo del despliegue..." style={{ width: '100%', padding: '6px', marginTop: '4px', height: '60px' }} />
              </label>

              {deployError ? <div style={{ fontSize: '12px', color: '#dc2626' }}>{deployError}</div> : null}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
                <button type="button" onClick={() => setShowDeployModal(false)} style={{ padding: '6px 12px', borderRadius: '4px', border: '1px solid #cbd5e1' }}>Cancelar</button>
                <button type="submit" disabled={deploying} style={{ padding: '6px 12px', borderRadius: '4px', border: 'none', backgroundColor: '#0284c7', color: '#ffffff', fontWeight: 600 }}>
                  {deploying ? 'Creando...' : 'Crear despliegue pendiente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </section>
  );
}
