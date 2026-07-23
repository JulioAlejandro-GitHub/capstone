import { useEffect,useState } from 'react';
import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { StatusBadge } from '../components/StatusBadge';
import { DEFAULT_DATASET_IMAGE_PAGE_SIZE } from '../config/pagination';
import { api } from '../services/api';
import type { DeploymentReadiness,DeploymentRow } from '../types/api';
import { formatDate,formatMetric } from '../utils/format';

const short=(value:string)=>`${value.slice(0,8)}…`;
export function Deployments({datasource,selectedDeploymentId,onExecutions,onModelVersionSelect}:{datasource:string;selectedDeploymentId:string|null;onExecutions:()=>void;onModelVersionSelect:(id:string)=>void}){
  const[rows,setRows]=useState<DeploymentRow[]>([]);const[loading,setLoading]=useState(true);const[error,setError]=useState<string|null>(null);
  const[selectedId,setSelectedId]=useState<string|null>(selectedDeploymentId);const[actor,setActor]=useState('operador-web');
  const[reason,setReason]=useState('Operación aprobada desde interfaz');const[sourceImageId,setSourceImageId]=useState('');
  const[confirmProduction,setConfirmProduction]=useState(false);const[busy,setBusy]=useState(false);const[notice,setNotice]=useState<string|null>(null);
  const[rollbackTarget,setRollbackTarget]=useState('');
  const[readiness,setReadiness]=useState<DeploymentReadiness|null>(null);const[readinessLoading,setReadinessLoading]=useState(false);
  const refresh=()=>{setLoading(true);setError(null);return Promise.all([api.getDeployments(datasource),api.getDatasetImages(datasource,{page:1,page_size:DEFAULT_DATASET_IMAGE_PAGE_SIZE})])
    .then(([deployments,images])=>{setRows(deployments.items);if(!sourceImageId&&images.items[0])setSourceImageId(images.items[0].image_id);})
    .catch(e=>{const detail=e instanceof Error?e.message:String(e);console.error('No fue posible cargar Despliegues',e);
      setError(detail.includes('page_size')?'No fue posible cargar los despliegues debido a una configuración de paginación inválida.':'No fue posible cargar los despliegues. Intenta nuevamente.');})
    .finally(()=>setLoading(false));};
  useEffect(()=>{void refresh();},[datasource]);
  const openDeployment=async(id:string)=>{setSelectedId(id);setReadiness(null);setReadinessLoading(true);setNotice(null);
    try{setReadiness(await api.getDeploymentReadiness(datasource,id));}catch(e){setNotice(e instanceof Error?e.message:String(e));}finally{setReadinessLoading(false);}};
  useEffect(()=>{if(selectedDeploymentId)openDeployment(selectedDeploymentId);else setSelectedId(null);},[selectedDeploymentId,datasource]);
  const selected=selectedId?rows.find(row=>row.id===selectedId)??null:null;
  const act=async(action:'smoke'|'activate'|'deactivate'|'retire'|'rollback')=>{if(!selected)return;setBusy(true);setNotice(null);
    try{
      if(action==='smoke'){if(!sourceImageId)throw new Error('No existe imagen controlada para el smoke test.');await api.smokeTestDeployment(datasource,selected.id,sourceImageId,actor);}
      else if(action==='activate')await api.activateDeployment(datasource,selected.id,actor,confirmProduction);
      else if(action==='rollback'){if(!rollbackTarget)throw new Error('Seleccione la revisión histórica objetivo.');await api.rollbackDeployment(datasource,selected.id,rollbackTarget,actor,reason);}
      else await api.transitionDeployment(datasource,selected.id,action,actor,reason);
      setNotice('Operación completada y auditada.');await refresh();await openDeployment(selected.id);
    }catch(e){setNotice(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
  };
  if(loading&&!rows.length)return <div className="page"><Loading/></div>;
  if(error)return <div className="page"><div className="panel warning-panel"><h1>Error al cargar deployments</h1><p>{error}</p><button type="button" onClick={refresh}>Reintentar</button></div></div>;
  return <section className="page"><div className="page-title"><div><h1>Despliegues</h1><p>Activación, retiro y evidencia operativa sobre revisiones inmutables.</p></div></div>
    <div className="panel"><DataTable rows={rows} emptyText="No existen deployments registrados." getRowKey={r=>r.id} columns={[
      {header:'Modelo / deployment',render:r=><><strong>{r.model_name??'Modelo no identificado'}{r.version_number?` · v${r.version_number}`:''}</strong><br/><span>{r.deployment_name}</span><br/><code>{short(r.id)}</code></>},{header:'Environment',render:r=>r.environment},
      {header:'Alias',render:r=><strong>{r.alias}</strong>},{header:'Model version',render:r=><code>{short(r.model_version_id)}</code>},
      {header:'Estado',render:r=><StatusBadge status={r.status}/>},{header:'Threshold',render:r=>formatMetric(r.threshold_value)},
      {header:'Activación',render:r=>formatDate(r.deployed_at)},{header:'Smoke',render:r=>String((r.metadata?.smoke_test as Record<string,unknown>|undefined)?.status??'PENDIENTE')},
      {header:'Acción',render:r=><button className="table-action" onClick={()=>openDeployment(r.id)}>Revisar y desplegar</button>}]}/></div>
    {selected?<div className="panel detail-panel" aria-live="polite"><div className="section-heading"><h2>{selected.deployment_name}</h2><StatusBadge status={selected.status}/></div>
      {readinessLoading?<Loading/>:readiness?<><div className={`deployment-readiness deployment-readiness--${readiness.can_activate?'ready':'blocked'}`}>
        <div><strong>{readiness.can_activate?'Listo para activar':'Aún no puede activarse en producción'}</strong><p>{readiness.can_activate?'Todos los requisitos técnicos están cumplidos. Confirma la activación.':'Revise los requisitos bloqueados antes de continuar.'}</p></div>
        <span>{readiness.requirements.filter(item=>item.status==='pass').length}/{readiness.requirements.filter(item=>item.status!=='not_applicable').length} requisitos</span></div>
        <div className="facts-grid"><span>Modelo<strong>{readiness.model_name} {readiness.version_number?`v${readiness.version_number}`:''}</strong></span><span>Model version<strong>{selected.model_version_id}</strong></span><span>Training run<strong>{readiness.training_run_id}</strong></span><span>Destino<strong>{selected.environment} / {selected.alias}</strong></span></div>
        <h3>Requisitos para desplegar</h3><ol className="deployment-checklist">{readiness.requirements.map(item=><li key={item.key} data-status={item.status}><span aria-hidden="true">{item.status==='pass'?'✓':item.status==='blocked'?'!':'○'}</span><div><strong>{item.label}</strong><p>{item.detail}</p></div></li>)}</ol>
      </>:null}
      <div className="filters-grid"><label>Responsable<input value={actor} onChange={e=>setActor(e.target.value)}/></label><label>Motivo<input value={reason} onChange={e=>setReason(e.target.value)}/></label>
        {selected.status==='active'?<label>Revisión para rollback<select value={rollbackTarget} onChange={e=>setRollbackTarget(e.target.value)}><option value="">Seleccione</option>{rows.filter(row=>row.id!==selected.id&&row.deployment_name===selected.deployment_name&&row.environment===selected.environment&&row.alias===selected.alias).map(row=><option value={row.id} key={row.id}>{short(row.id)} · {row.status}</option>)}</select></label>:null}
        {selected.environment==='production'&&readiness?.can_activate?<label className="production-confirmation"><input type="checkbox" checked={confirmProduction} onChange={e=>setConfirmProduction(e.target.checked)}/> Confirmo que este modelo será el champion de producción</label>:null}</div>
      {['pending','inactive'].includes(selected.status)?<details className="advanced-options"><summary>Configuración avanzada del smoke test</summary><label>Imagen controlada<input value={sourceImageId} onChange={e=>setSourceImageId(e.target.value)}/></label><small>Se selecciona automáticamente una imagen registrada. Cambie este ID solo para una validación controlada específica.</small></details>:null}
      {notice?<div className="warning-panel" role="status">{notice}</div>:null}
      <div className="detail-actions">
        {['pending','inactive'].includes(selected.status)?<button disabled={busy||readinessLoading||!readiness?.can_run_smoke||!sourceImageId} onClick={()=>act('smoke')}>1. Validar modelo</button>:null}
        {['pending','inactive'].includes(selected.status)?<button className="primary-action" disabled={busy||!readiness?.can_activate||(selected.environment==='production'&&!confirmProduction)} onClick={()=>act('activate')}>2. Activar{selected.environment==='production'?' en producción':''}</button>:null}
        {selected.status==='active'?<button disabled={busy} onClick={()=>act('deactivate')}>Desactivar</button>:null}
        {selected.status==='active'?<button disabled={busy||!rollbackTarget||!reason.trim()} onClick={()=>act('rollback')}>Crear rollback pendiente</button>:null}
        {selected.status!=='retired'?<button disabled={busy} onClick={()=>act('retire')}>Retirar</button>:null}
        {readiness&&!readiness.can_run_smoke?<button type="button" onClick={()=>onModelVersionSelect(selected.model_version_id)}>Revisar modelo liberado</button>:null}
        <button type="button" onClick={onExecutions}>Volver a Ejecuciones</button>
      </div>{readiness&&!readiness.can_run_smoke&&selected.status==='pending'?<p className="api-note">Este deployment no puede repararse desde esta pantalla: complete los snapshots indicados en la model version o prepare una nueva versión liberable desde Ejecuciones.</p>:null}<p className="api-note">El rollback crea una revisión pendiente nueva; nunca reactiva ni sobrescribe una revisión histórica.</p></div>:null}
  </section>;
}
