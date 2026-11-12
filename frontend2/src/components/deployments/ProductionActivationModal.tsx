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
  return <div className="fixed inset-0 z-[1000] grid place-items-center bg-[rgba(16,24,43,0.58)] p-5" role="presentation"><div ref={dialogRef} className="grid gap-3.5 w-[min(620px,100%)] max-h-[calc(100vh-40px)] overflow-auto rounded-modal bg-surface p-6 shadow-modal" role="dialog" aria-modal="true" aria-labelledby="production-modal-title">
    <h2 className="m-0" id="production-modal-title">Publicar {identity(deployment)} en producción</h2>
    <p className="m-0">Vas a publicar <strong>{identity(deployment)}</strong> como champion de producción.</p>
    <p className="m-0">La operación crea o reutiliza una revisión production pendiente, ejecuta el smoke test con una imagen controlada y solo activa si el resultado es PASS.</p>
    {currentChampion?<p className="rounded-step border border-[#efc275] bg-[#fff8e8] p-3">Esta operación reemplazará a <strong>{identity(currentChampion)}</strong>. La versión anterior se conservará para rollback.</p>:<p className="m-0">No existe un champion de producción activo que deba reemplazarse.</p>}
    <dl className="m-0 grid grid-cols-2 gap-2 max-[700px]:grid-cols-1"><div className="rounded-lg border border-[#e4e9f2] p-2.25"><dt className="text-muted text-xs">Model version</dt><dd className="mt-0.75 font-bold overflow-wrap-anywhere">{short(deployment.model_version_id)}</dd></div><div className="rounded-lg border border-[#e4e9f2] p-2.25"><dt className="text-muted text-xs">Deployment</dt><dd className="mt-0.75 font-bold overflow-wrap-anywhere">{short(deployment.id)}</dd></div>
      <div className="rounded-lg border border-[#e4e9f2] p-2.25"><dt className="text-muted text-xs">Destino</dt><dd className="mt-0.75 font-bold overflow-wrap-anywhere">production / champion</dd></div><div className="rounded-lg border border-[#e4e9f2] p-2.25"><dt className="text-muted text-xs">Threshold</dt><dd className="mt-0.75 font-bold overflow-wrap-anywhere">{formatMetric(deployment.threshold_value)}</dd></div>
      <div className="rounded-lg border border-[#e4e9f2] p-2.25"><dt className="text-muted text-xs">Smoke production</dt><dd className="mt-0.75 font-bold overflow-wrap-anywhere">{deployment.environment==='production'?String(readiness.smoke_test?.status??'PENDIENTE'):'Se ejecutará'}</dd></div></dl>
    <div className="grid grid-cols-[repeat(auto-fit,minmax(190px,1fr))] gap-3.5"><label className="grid gap-1.5 text-muted text-sm">Responsable<input className="w-full rounded-step border border-border-strong bg-surface p-2.25 text-ink-strong" value={actor} onChange={event=>onActor(event.target.value)}/></label><label className="grid gap-1.5 text-muted text-sm">Motivo<textarea className="w-full rounded-step border border-border-strong bg-surface p-2.25 text-ink-strong" value={reason} onChange={event=>onReason(event.target.value)}/></label></div>
    <label className="my-4 flex items-center gap-2 font-bold"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/> Confirmo la publicación en producción.</label>
    {busy?<ol className="rounded-step border border-[#dbe2ef] bg-[#f6f8fc] p-3 pl-8.5">{progress.map((item,index)=><li key={item} data-state={index===0?'running':'pending'} className="data-[state=running]:text-[#294f9f] data-[state=running]:font-bold">{item}</li>)}</ol>:null}
    <div className="flex justify-end gap-2.5"><button type="button" className="focus-visible:outline-3 focus-visible:outline-[#82a7ef] focus-visible:outline-offset-2" onClick={onCancel} disabled={busy}>Cancelar</button><button type="button" className="bg-[#9f2929] text-white focus-visible:outline-3 focus-visible:outline-[#82a7ef] focus-visible:outline-offset-2" onClick={onConfirm} disabled={busy||!confirmed||!actor.trim()||!reason.trim()}>{busy?'Publicando…':'Publicar en producción'}</button></div>
  </div></div>;
}
