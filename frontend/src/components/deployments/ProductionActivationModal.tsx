import { useEffect,useRef,useState } from 'react';
import type { DeploymentReadiness,DeploymentRow } from '../../types/api';
import { formatMetric } from '../../utils/format';

const short=(value:string)=>`${value.slice(0,8)}…`;
const identity=(deployment:DeploymentRow)=>`${deployment.model_name??'Modelo'}${deployment.version_number?` v${deployment.version_number}`:''}`;

export function ProductionActivationModal({deployment,readiness,currentChampion,busy,actor,reason,progress,onActor,onReason,onCancel,onConfirm}:{deployment:DeploymentRow;readiness:DeploymentReadiness;currentChampion:DeploymentRow|null;busy:boolean;actor:string;reason:string;progress:string[];onActor:(value:string)=>void;onReason:(value:string)=>void;onCancel:()=>void;onConfirm:()=>void}){
  const dialogRef=useRef<HTMLDivElement>(null);
  const[confirmed,setConfirmed]=useState(false);
  useEffect(()=>{
    const dialog=dialogRef.current;const focusable=()=>Array.from(dialog?.querySelectorAll<HTMLElement>('button:not([disabled])')??[]);
    focusable()[0]?.focus();
    const onKey=(event:KeyboardEvent)=>{if(event.key==='Escape'){event.preventDefault();onCancel();return;}if(event.key!=='Tab')return;
      const items=focusable();if(!items.length)return;const first=items[0],last=items[items.length-1];
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    };
    document.addEventListener('keydown',onKey);return()=>document.removeEventListener('keydown',onKey);
  },[onCancel]);
  return <div className="modal-backdrop" role="presentation"><div ref={dialogRef} className="production-modal" role="dialog" aria-modal="true" aria-labelledby="production-modal-title">
    <h2 id="production-modal-title">Publicar {identity(deployment)} en producción</h2>
    <p>Vas a publicar <strong>{identity(deployment)}</strong> como champion de producción.</p>
    <p>La operación crea o reutiliza una revisión production pendiente, ejecuta el smoke test con una imagen controlada y solo activa si el resultado es PASS.</p>
    {currentChampion?<p className="modal-warning">Esta operación reemplazará a <strong>{identity(currentChampion)}</strong>. La versión anterior se conservará para rollback.</p>:<p>No existe un champion de producción activo que deba reemplazarse.</p>}
    <dl className="modal-facts"><div><dt>Model version</dt><dd>{short(deployment.model_version_id)}</dd></div><div><dt>Deployment</dt><dd>{short(deployment.id)}</dd></div>
      <div><dt>Destino</dt><dd>production / champion</dd></div><div><dt>Threshold</dt><dd>{formatMetric(deployment.threshold_value)}</dd></div>
      <div><dt>Smoke production</dt><dd>{deployment.environment==='production'?String(readiness.smoke_test?.status??'PENDIENTE'):'Se ejecutará'}</dd></div></dl>
    <div className="filters-grid"><label>Responsable<input value={actor} onChange={event=>onActor(event.target.value)}/></label><label>Motivo<textarea value={reason} onChange={event=>onReason(event.target.value)}/></label></div>
    <label className="production-confirmation"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/> Confirmo la publicación en producción.</label>
    {busy?<ol className="publication-progress">{progress.map((item,index)=><li key={item} data-state={index===0?'running':'pending'}>{item}</li>)}</ol>:null}
    <div className="modal-actions"><button type="button" onClick={onCancel} disabled={busy}>Cancelar</button><button type="button" className="danger-action" onClick={onConfirm} disabled={busy||!confirmed||!actor.trim()||!reason.trim()}>{busy?'Publicando…':'Publicar en producción'}</button></div>
  </div></div>;
}
