import { useEffect, useMemo, useState } from 'react';
import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type { DeploymentRow, ModelVersionLineageRow, ModelVersionRow, TrainingPromotionStatus } from '../types/api';
import { formatDate, formatMetric } from '../utils/format';

const short=(value:string|null|undefined,size=8)=>value ? `${value.slice(0,size)}…` : '—';
export function ModelVersions({datasource,onRunSelect,onDeploymentSelect,onDeployments,onExecutions,selectedModelVersionId}:{datasource:string;onRunSelect:(id:string)=>void;onDeploymentSelect:(id:string)=>void;onDeployments:()=>void;onExecutions:()=>void;selectedModelVersionId:string|null}) {
  const [rows,setRows]=useState<ModelVersionRow[]>([]);const [deployments,setDeployments]=useState<DeploymentRow[]>([]);
  const [loading,setLoading]=useState(true);const [error,setError]=useState<string|null>(null);
  const [model,setModel]=useState('');const [status,setStatus]=useState('');const [lineage,setLineage]=useState('');
  const [selected,setSelected]=useState<ModelVersionRow|null>(null);const [lineageRows,setLineageRows]=useState<ModelVersionLineageRow[]>([]);
  const [selectedPromotion,setSelectedPromotion]=useState<TrainingPromotionStatus|null>(null);
  const [actor,setActor]=useState('operador-web');const [reason,setReason]=useState('');
  const [environment,setEnvironment]=useState('experimental');const [alias,setAlias]=useState('champion');
  const [busy,setBusy]=useState(false);const [actionError,setActionError]=useState<string|null>(null);
  useEffect(()=>{setLoading(true);setError(null);Promise.all([api.getModelVersions(datasource),api.getDeployments(datasource)])
    .then(([versions,allDeployments])=>{setRows(versions.items);setDeployments(allDeployments.items)}).catch((reason)=>setError(String(reason))).finally(()=>setLoading(false));},[datasource]);
  useEffect(()=>{if(!loading&&selectedModelVersionId){const match=rows.find((row)=>row.id===selectedModelVersionId);if(match)open(match);}},[loading,rows,selectedModelVersionId]);
  const filtered=useMemo(()=>rows.filter((row)=>(!model||row.model_name===model)&&(!status||row.status===status)&&(!lineage||row.lineage_status===lineage)),[rows,model,status,lineage]);
  const open=(row:ModelVersionRow)=>{setSelected(row);setSelectedPromotion(null);Promise.all([
    api.getModelVersion(datasource,row.id),
    api.getModelVersionLineage(datasource,row.id),
    api.getTrainingPromotionStatus(datasource,row.training_run_id),
  ]).then(([detail,lineageResult,promotion])=>{setSelected({...row,...detail});setLineageRows(lineageResult.items);setSelectedPromotion(promotion);})
    .catch(()=>{setLineageRows([]);setSelectedPromotion(null);});};
  const runAction=async(action:'validate'|'approve'|'deploy')=>{
    if(!selected)return;setBusy(true);setActionError(null);
    try{
      if(action==='validate'){
        if(!selected.threshold_profile_id)throw new Error('No existe threshold profile asociado.');
        await api.validateModelVersion(datasource,selected.id,selected.threshold_profile_id,actor,reason||'Validación técnica desde interfaz');
        open(selected);
      }else if(action==='approve'){
        if(!reason.trim())throw new Error('La aprobación requiere un motivo.');
        await api.approveModelVersion(datasource,selected.id,actor,reason);open(selected);
      }else{
        if(!selected.threshold_profile_id)throw new Error('No existe threshold profile asociado.');
        const deployment=await api.createDeployment(datasource,{model_version_id:selected.id,deployment_name:`${selected.model_name}-service`,environment,alias,threshold_profile_id:selected.threshold_profile_id,deployed_by:actor});
        onDeploymentSelect(deployment.id);
      }
    }catch(e){setActionError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
  };
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
      {header:'Operación',render:(row)=>{const active=deployments.find((item)=>item.model_version_id===row.id&&item.status==='active');return active?<span>{active.metadata?.production_scope==='stage2_technical'?<strong className="production-run-badge">Productivo Etapa 2</strong>:active.alias}<br/><small>{active.environment} / {active.alias}</small></span>:'Sin deployment activo'}},
      {header:'Detalle',render:(row)=><button type="button" className="table-action" onClick={()=>open(row)}>Ver detalle</button>},]}/></div>
    {selected?<div className="panel detail-panel"><div className="section-heading"><h2>{selected.model_name} · v{selected.version_number??'—'}</h2><button type="button" onClick={()=>setSelected(null)}>Cerrar</button></div>
      <div className="facts-grid"><span>Model version<strong>{selected.id}</strong></span><span>Training run<strong>{selected.training_run_id}</strong></span><span>Linaje<strong>{selected.lineage_status}</strong></span><span>Evaluación<strong>{selectedPromotion?.evaluation_run_id?short(selectedPromotion.evaluation_run_id,12):'No vinculada'}</strong></span>
        <span>Explicabilidad<strong>{selectedPromotion?.explainability_run_ids.length?'Disponible':'Opcional / no registrada'}</strong></span><span>Threshold<strong>{selectedPromotion?.threshold?formatMetric(selectedPromotion.threshold.value):'No validado'}</strong></span>
        <span>Preprocessing<strong>{selected.preprocessing_profile_snapshot&&Object.keys(selected.preprocessing_profile_snapshot).length?JSON.stringify(selected.preprocessing_profile_snapshot):'No registrado'}</strong></span><span>SHA-256<strong>{short(selected.artifact_sha256,12)}</strong></span>
        <span>Puede desplegarse<strong>{selectedPromotion?.can_deploy?'Sí':'No'}</strong></span><span>Deployments relacionados<strong>{deployments.filter((item)=>item.model_version_id===selected.id).length}</strong></span></div>
      {selectedPromotion?.blocking_reasons.length?<div className="warning-panel" role="status"><strong>Requisitos pendientes</strong><ul>{selectedPromotion.blocking_reasons.map((reason)=><li key={reason.code}>{reason.message}</li>)}</ul></div>:null}
      <div className="filters-grid"><label>Responsable<input value={actor} onChange={e=>setActor(e.target.value)}/></label><label>Motivo<input value={reason} onChange={e=>setReason(e.target.value)}/></label>
        <label>Ambiente<select value={environment} onChange={e=>setEnvironment(e.target.value)}><option value="experimental">experimental</option><option value="staging">staging</option><option value="production">production</option></select></label>
        <label>Alias<select value={alias} onChange={e=>setAlias(e.target.value)}><option value="champion">champion</option><option value="candidate">candidate</option></select></label></div>
      {actionError?<div className="warning-panel" role="alert">{actionError}</div>:null}
      <div className="detail-actions">
        {['candidate','discovered'].includes(selected.status)?<button disabled={busy||!selected.threshold_profile_id} onClick={()=>runAction('validate')}>Validar</button>:null}
        {selected.status==='validated'?<button disabled={busy||!reason.trim()} onClick={()=>runAction('approve')}>Aprobar</button>:null}
        {['approved','deployed'].includes(selected.status)?<button disabled={busy||!selected.threshold_profile_id} onClick={()=>runAction('deploy')}>Crear deployment pendiente</button>:null}
      </div>
      <h3>Linaje</h3>{lineageRows.length?<ol className="lineage-list">{lineageRows.map((item)=><li key={item.id}><strong>{item.relationship_type}</strong><code>{short(item.child_run_id,12)}</code>{item.relationship_type.includes('evaluates')?<button type="button" onClick={()=>onRunSelect(item.child_run_id)}>Ver evaluación</button>:null}</li>)}</ol>:<p className="empty-state">Sin relaciones registradas.</p>}
      <div className="detail-actions"><button type="button" className="table-action" onClick={onDeployments}>Ver deployments</button><button type="button" onClick={onExecutions}>Volver a Ejecuciones</button></div>
      <p className="api-note">Las transiciones registran responsable y motivo; la autorización corporativa debe integrarse con el proveedor de identidad antes de exposición pública.</p></div>:null}
  </section>;
}
