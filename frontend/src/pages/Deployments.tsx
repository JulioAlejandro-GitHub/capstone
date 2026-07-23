import { useEffect,useState } from 'react';
import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { StatusBadge } from '../components/StatusBadge';
import { DEFAULT_DATASET_IMAGE_PAGE_SIZE } from '../config/pagination';
import { api } from '../services/api';
import type { DeploymentRow } from '../types/api';
import { formatDate,formatMetric } from '../utils/format';

const short=(value:string)=>`${value.slice(0,8)}…`;
export function Deployments({datasource,selectedDeploymentId,onExecutions}:{datasource:string;selectedDeploymentId:string|null;onExecutions:()=>void}){
  const[rows,setRows]=useState<DeploymentRow[]>([]);const[loading,setLoading]=useState(true);const[error,setError]=useState<string|null>(null);
  const[selectedId,setSelectedId]=useState<string|null>(selectedDeploymentId);const[actor,setActor]=useState('operador-web');
  const[reason,setReason]=useState('Operación aprobada desde interfaz');const[sourceImageId,setSourceImageId]=useState('');
  const[confirmProduction,setConfirmProduction]=useState(false);const[busy,setBusy]=useState(false);const[notice,setNotice]=useState<string|null>(null);
  const[rollbackTarget,setRollbackTarget]=useState('');
  const refresh=()=>{setLoading(true);setError(null);Promise.all([api.getDeployments(datasource),api.getDatasetImages(datasource,{page:1,page_size:DEFAULT_DATASET_IMAGE_PAGE_SIZE})])
    .then(([deployments,images])=>{setRows(deployments.items);if(!sourceImageId&&images.items[0])setSourceImageId(images.items[0].image_id);})
    .catch(e=>{const detail=e instanceof Error?e.message:String(e);console.error('No fue posible cargar Despliegues',e);
      setError(detail.includes('page_size')?'No fue posible cargar los despliegues debido a una configuración de paginación inválida.':'No fue posible cargar los despliegues. Intenta nuevamente.');})
    .finally(()=>setLoading(false));};
  useEffect(refresh,[datasource]);
  useEffect(()=>setSelectedId(selectedDeploymentId),[selectedDeploymentId]);
  const selected=selectedId?rows.find(row=>row.id===selectedId)??null:null;
  const smoke=(selected?.metadata?.smoke_test as Record<string,unknown>|undefined);
  const act=async(action:'smoke'|'activate'|'deactivate'|'retire'|'rollback')=>{if(!selected)return;setBusy(true);setNotice(null);
    try{
      if(action==='smoke'){if(!sourceImageId)throw new Error('No existe imagen controlada para el smoke test.');await api.smokeTestDeployment(datasource,selected.id,sourceImageId,actor);}
      else if(action==='activate')await api.activateDeployment(datasource,selected.id,actor,confirmProduction);
      else if(action==='rollback'){if(!rollbackTarget)throw new Error('Seleccione la revisión histórica objetivo.');await api.rollbackDeployment(datasource,selected.id,rollbackTarget,actor,reason);}
      else await api.transitionDeployment(datasource,selected.id,action,actor,reason);
      setNotice('Operación completada y auditada.');refresh();
    }catch(e){setNotice(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
  };
  if(loading&&!rows.length)return <div className="page"><Loading/></div>;
  if(error)return <div className="page"><div className="panel warning-panel"><h1>Error al cargar deployments</h1><p>{error}</p><button type="button" onClick={refresh}>Reintentar</button></div></div>;
  return <section className="page"><div className="page-title"><div><h1>Despliegues</h1><p>Activación, retiro y evidencia operativa sobre revisiones inmutables.</p></div></div>
    <div className="panel"><DataTable rows={rows} emptyText="No existen deployments registrados." getRowKey={r=>r.id} columns={[
      {header:'Deployment',render:r=><><strong>{r.deployment_name}</strong><br/><code>{short(r.id)}</code></>},{header:'Environment',render:r=>r.environment},
      {header:'Alias',render:r=><strong>{r.alias}</strong>},{header:'Model version',render:r=><code>{short(r.model_version_id)}</code>},
      {header:'Estado',render:r=><StatusBadge status={r.status}/>},{header:'Threshold',render:r=>formatMetric(r.threshold_value)},
      {header:'Activación',render:r=>formatDate(r.deployed_at)},{header:'Smoke',render:r=>String((r.metadata?.smoke_test as Record<string,unknown>|undefined)?.status??'PENDIENTE')},
      {header:'Detalle',render:r=><button onClick={()=>setSelectedId(r.id)}>Administrar</button>}]}/></div>
    {selected?<div className="panel detail-panel" aria-live="polite"><div className="section-heading"><h2>{selected.deployment_name}</h2><StatusBadge status={selected.status}/></div>
      <div className="facts-grid"><span>Deployment<strong>{selected.id}</strong></span><span>Model version<strong>{selected.model_version_id}</strong></span><span>Ambiente<strong>{selected.environment}</strong></span><span>Alias<strong>{selected.alias}</strong></span><span>Smoke test<strong>{String(smoke?.status??'PENDIENTE')}</strong></span><span>Errores smoke<strong>{JSON.stringify(smoke?.errors??[])}</strong></span></div>
      <div className="filters-grid"><label>Responsable<input value={actor} onChange={e=>setActor(e.target.value)}/></label><label>Motivo<input value={reason} onChange={e=>setReason(e.target.value)}/></label><label>Imagen controlada<input value={sourceImageId} onChange={e=>setSourceImageId(e.target.value)}/></label>
        {selected.status==='active'?<label>Revisión para rollback<select value={rollbackTarget} onChange={e=>setRollbackTarget(e.target.value)}><option value="">Seleccione</option>{rows.filter(row=>row.id!==selected.id&&row.deployment_name===selected.deployment_name&&row.environment===selected.environment&&row.alias===selected.alias).map(row=><option value={row.id} key={row.id}>{short(row.id)} · {row.status}</option>)}</select></label>:null}
        {selected.environment==='production'?<label><input type="checkbox" checked={confirmProduction} onChange={e=>setConfirmProduction(e.target.checked)}/> Confirmo activación en producción</label>:null}</div>
      {notice?<div className="warning-panel" role="status">{notice}</div>:null}
      <div className="detail-actions">
        {['pending','inactive'].includes(selected.status)?<button disabled={busy||!sourceImageId} onClick={()=>act('smoke')}>Ejecutar smoke test</button>:null}
        {['pending','inactive'].includes(selected.status)?<button disabled={busy||smoke?.status!=='PASS'||(selected.environment==='production'&&!confirmProduction)} onClick={()=>act('activate')}>Activar{selected.environment==='production'?' en producción':''}</button>:null}
        {selected.status==='active'?<button disabled={busy} onClick={()=>act('deactivate')}>Desactivar</button>:null}
        {selected.status==='active'?<button disabled={busy||!rollbackTarget||!reason.trim()} onClick={()=>act('rollback')}>Crear rollback pendiente</button>:null}
        {selected.status!=='retired'?<button disabled={busy} onClick={()=>act('retire')}>Retirar</button>:null}
        <button type="button" onClick={onExecutions}>Volver a Ejecuciones</button>
      </div><p className="api-note">El rollback crea una revisión pendiente nueva; nunca reactiva ni sobrescribe una revisión histórica.</p></div>:null}
  </section>;
}
