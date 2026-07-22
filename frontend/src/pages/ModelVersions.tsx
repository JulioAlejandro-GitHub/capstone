import { useEffect, useMemo, useState } from 'react';
import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type { DeploymentRow, ModelVersionLineageRow, ModelVersionRow } from '../types/api';
import { formatDate, formatMetric } from '../utils/format';

const short=(value:string|null|undefined,size=8)=>value ? `${value.slice(0,size)}…` : '—';
export function ModelVersions({datasource,onRunSelect,onDeployments}:{datasource:string;onRunSelect:(id:string)=>void;onDeployments:()=>void}) {
  const [rows,setRows]=useState<ModelVersionRow[]>([]);const [deployments,setDeployments]=useState<DeploymentRow[]>([]);
  const [loading,setLoading]=useState(true);const [error,setError]=useState<string|null>(null);
  const [model,setModel]=useState('');const [status,setStatus]=useState('');const [lineage,setLineage]=useState('');
  const [selected,setSelected]=useState<ModelVersionRow|null>(null);const [lineageRows,setLineageRows]=useState<ModelVersionLineageRow[]>([]);
  useEffect(()=>{setLoading(true);setError(null);Promise.all([api.getModelVersions(datasource),api.getDeployments(datasource,true)])
    .then(([versions,active])=>{setRows(versions.items);setDeployments(active.items)}).catch((reason)=>setError(String(reason))).finally(()=>setLoading(false));},[datasource]);
  const filtered=useMemo(()=>rows.filter((row)=>(!model||row.model_name===model)&&(!status||row.status===status)&&(!lineage||row.lineage_status===lineage)),[rows,model,status,lineage]);
  const open=(row:ModelVersionRow)=>{setSelected(row);api.getModelVersionLineage(datasource,row.id).then((result)=>setLineageRows(result.items)).catch(()=>setLineageRows([]));};
  if(loading)return <div className="page"><Loading/></div>;
  if(error)return <div className="page"><div className="panel warning-panel"><h1>No se pudieron cargar los modelos liberados</h1><p>{error}</p></div></div>;
  const models=[...new Set(rows.map((row)=>row.model_name))];const statuses=[...new Set(rows.map((row)=>row.status))];const lineages=[...new Set(rows.map((row)=>row.lineage_status))];
  return <section className="page"><div className="page-title"><div><h1>Modelos liberados</h1><p>Versiones inmutables, su evaluación y estado operativo.</p></div></div>
    <div className="panel filter-bar"><label>Modelo<select value={model} onChange={(e)=>setModel(e.target.value)}><option value="">Todos</option>{models.map(x=><option key={x}>{x}</option>)}</select></label>
      <label>Estado<select value={status} onChange={(e)=>setStatus(e.target.value)}><option value="">Todos</option>{statuses.map(x=><option key={x}>{x}</option>)}</select></label>
      <label>Linaje<select value={lineage} onChange={(e)=>setLineage(e.target.value)}><option value="">Todos</option>{lineages.map(x=><option key={x}>{x}</option>)}</select></label></div>
    <div className="panel"><DataTable rows={filtered} emptyText="No hay model versions para los filtros seleccionados." getRowKey={(row)=>row.id} columns={[
      {header:'Modelo / versión',render:(row)=><><strong>{row.model_name}</strong><br/><small>v{row.version_number??'—'} · {short(row.id)}</small></>},
      {header:'Estado',render:(row)=><><StatusBadge status={row.status}/><br/><small>{row.lineage_status}</small></>},
      {header:'Training',render:(row)=><code>{short(row.training_run_id)}</code>},{header:'SHA-256',render:(row)=><code>{short(row.artifact_sha256,12)}</code>},
      {header:'Evaluación',render:(row)=><><span>Recall {formatMetric(row.recall_parasitized)}</span><br/><span>Spec. {formatMetric(row.specificity)}</span><br/><span>F2 {formatMetric(row.f2_parasitized)}</span></>},
      {header:'Threshold',render:(row)=>formatMetric(row.threshold_used)},{header:'Creado',render:(row)=>formatDate(row.created_at)},
      {header:'Operación',render:(row)=>{const active=deployments.find((item)=>item.model_version_id===row.id);return active?<span>{active.alias}<br/><small>{active.environment}</small></span>:'Sin deployment activo'}},
      {header:'Detalle',render:(row)=><button type="button" className="table-action" onClick={()=>open(row)}>Ver detalle</button>},]}/></div>
    {selected?<div className="panel detail-panel"><div className="section-heading"><h2>{selected.model_name} · v{selected.version_number??'—'}</h2><button type="button" onClick={()=>setSelected(null)}>Cerrar</button></div>
      <div className="facts-grid"><span>Model version<strong>{selected.id}</strong></span><span>Training run<strong>{selected.training_run_id}</strong></span><span>Linaje<strong>{selected.lineage_status}</strong></span><span>Explicabilidad<strong>{selected.explainability_available?'Disponible':'No registrada'}</strong></span></div>
      <h3>Linaje</h3>{lineageRows.length?<ol className="lineage-list">{lineageRows.map((item)=><li key={item.id}><strong>{item.relationship_type}</strong><code>{short(item.child_run_id,12)}</code>{item.relationship_type.includes('evaluates')?<button type="button" onClick={()=>onRunSelect(item.child_run_id)}>Ver evaluación</button>:null}</li>)}</ol>:<p className="empty-state">Sin relaciones registradas.</p>}
      <button type="button" className="table-action" onClick={onDeployments}>Ver deployments</button></div>:null}
  </section>;
}
