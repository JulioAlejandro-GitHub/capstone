import { useState } from 'react';
import type { Stage2Availability } from '../../types/api';

interface Props {
  id:string;status?:Stage2Availability;loading?:boolean;error?:string;
  explainCount:number;
  onPublish:(replaceExisting:boolean)=>Promise<'published'|'replacement-required'|'failed'>;
  onDeactivate:()=>Promise<void>;
}

const value=(raw?:string|null)=>raw||'No registrado';
const date=(raw?:string|null)=>raw?new Intl.DateTimeFormat('es-CL',{
  dateStyle:'medium',timeStyle:'short',
}).format(new Date(raw)):'No registrada';

export function Stage2PublicationPanel({
  id,status,loading=false,error,explainCount,onPublish,onDeactivate,
}:Props) {
  const [confirm,setConfirm]=useState<'publish'|'replace'|'deactivate'|null>(null);
  const active=Boolean(status?.is_stage2_available);
  const execute=async()=>{
    if(confirm==='publish'||confirm==='replace'){
      const result=await onPublish(confirm==='replace');
      if(result==='replacement-required'){setConfirm('replace');return;}
      if(result==='failed')return;
    }else if(confirm==='deactivate')await onDeactivate();
    setConfirm(null);
  };
  const publishable=Boolean(status?.eligible&&!status?.technical_blockers?.length);
  if (loading && !status) return <section aria-label="Detalle de disponibilidad para Etapa 2"
    className="stage2-publication-panel" id={id}>
    <p role="status">Consultando disponibilidad para Etapa 2…</p>
  </section>;
  return <section aria-label="Detalle de disponibilidad para Etapa 2"
    className="stage2-publication-panel" id={id}>
    <header>
      <div><h3>{active?'Modelo disponible para Etapa 2':'Disponibilizar modelo para Etapa 2'}</h3>
        <p>{active
          ?'Esta versión se encuentra activa como candidata para el procesamiento de imágenes de frotis completo.'
          :status?.eligible
            ?'TRAIN y EVALUATE están completados. Esta versión puede quedar disponible como candidata para el procesamiento de imágenes de frotis completo en la Etapa 2.'
            :'La versión no cumple la regla mínima de elegibilidad.'}</p></div>
      <strong className={active?'stage2-production-badge':'stage2-eligibility-badge'}>
        {active?'✓ Productivo Etapa 2':status?.eligible?'Elegible':'No disponible'}
      </strong>
    </header>
    <div className="stage2-publication-grid">
      <span>Regla<strong>TRAIN completed + EVALUATE completed</strong></span>
      <span>TRAIN<strong>{value(status?.training_run_id)} · {value(status?.train_status)}</strong></span>
      <span>EVALUATE<strong>{value(status?.evaluation_run_id)} · {value(status?.evaluation_status)}</strong></span>
      <span>EXPLAIN<strong>{explainCount?`${explainCount} asociado(s) · informativo`:'No registrado · opcional'}</strong></span>
      <span>Versión del modelo<strong>{value(status?.model_version_id)}</strong></span>
      <span>Modelo / checkpoint<strong>{value(status?.model_name)} · {value(status?.checkpoint)}</strong></span>
      <span>Estado Etapa 2<strong>{active?'Activo para nuevos trabajos':status?.eligible?'Disponible para publicar':'No disponible'}</strong></span>
      {status?.deployment_id?<><span>Deployment<strong>{status.deployment_id.slice(0,8)}</strong></span>
        <span>Slot productivo<strong>{status.environment} / {status.alias}</strong></span>
        <span>Threshold<strong>{status.threshold??'Registrado'} · {status.threshold_source??'fuente registrada'}</strong></span>
        <span>Desplegado<strong>{date(status.deployed_at)}</strong></span></>:null}
      {status?.publication?<><span>Publicación<strong>{status.publication.id}</strong></span>
        <span>Publicado<strong>{date(status.publication.published_at)} · {value(status.publication.published_by)}</strong></span></>:null}
    </div>
    {!publishable?<p className="stage2-missing-condition" role="status">
      {status?.technical_blockers?.map((item)=>item.message).join(' · ')
        ||status?.eligibility?.missing_conditions.join(' · ')||'Estado no elegible.'}
    </p>:null}
    <p className="stage2-experimental-warning">
      Esta publicación es técnica y experimental. No constituye aprobación clínica ni diagnóstico automatizado.
    </p>
    {error?<p className="run-promotion-error" role="alert">{error}</p>:null}
    {confirm?<div className="stage2-inline-confirmation" role="alert">
      <p>{confirm==='publish'
        ?'Se publicará una referencia inmutable de esta versión. La Etapa 2 podrá seleccionarla para nuevos análisis.'
        :confirm==='replace'
          ?'Ya existe un modelo elegido para Etapa 2. Si continúas, el modelo anterior dejará de estar elegido y esta versión pasará a ser la nueva elegida.'
        :'Los análisis anteriores conservarán su trazabilidad. El modelo dejará de estar disponible únicamente para nuevos trabajos de Etapa 2.'}</p>
      <div><button className={confirm==='deactivate'?'':'primary-action'} disabled={loading}
        onClick={()=>void execute()} type="button">{confirm==='publish'?'Confirmar publicación':confirm==='replace'?'Continuar y reemplazar':'Confirmar baja'}</button>
        <button disabled={loading} onClick={()=>setConfirm(null)} type="button">Cancelar</button></div>
    </div>:active||publishable?<button className={active?'':'primary-action'} disabled={loading}
      onClick={()=>setConfirm(active?'deactivate':'publish')} type="button">
      {active?'Dar de baja de Etapa 2':'Publicar y desplegar en Etapa 2'}
    </button>:<button disabled title={status?.technical_blockers?.map((item)=>item.message).join(', ')
      ||status?.eligibility?.missing_conditions.join(', ')}
      type="button">Publicar y desplegar en Etapa 2</button>}
  </section>;
}
