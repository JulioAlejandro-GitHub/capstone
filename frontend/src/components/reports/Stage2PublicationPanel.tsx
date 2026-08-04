import { useState } from 'react';
import type { Stage2PublicationStatus } from '../../types/api';

interface Props {
  id:string;status?:Stage2PublicationStatus;loading?:boolean;error?:string;
  explainCount:number;onPublish:()=>Promise<void>;onDeactivate:()=>Promise<void>;
}

const value=(raw?:string|null)=>raw||'No registrado';
const date=(raw?:string|null)=>raw?new Intl.DateTimeFormat('es-CL',{
  dateStyle:'medium',timeStyle:'short',
}).format(new Date(raw)):'No registrada';

export function Stage2PublicationPanel({
  id,status,loading=false,error,explainCount,onPublish,onDeactivate,
}:Props) {
  const [confirm,setConfirm]=useState<'publish'|'deactivate'|null>(null);
  const active=Boolean(status?.publication?.is_active);
  const canPublish=Boolean(status?.eligible&&status.model_version_id);
  const execute=async()=>{if(confirm==='publish')await onPublish();else if(confirm==='deactivate')await onDeactivate();setConfirm(null);};
  return <section aria-label="Detalle de publicación para Etapa 2"
    className="stage2-publication-panel" id={id}>
    <header>
      <div><h3>{active?'Modelo publicado para Etapa 2':'Publicar modelo para Etapa 2'}</h3>
        <p>{active
          ?'Esta versión está activa en el catálogo de candidatos para nuevos análisis.'
          :status?.eligible
            ?'TRAIN y EVALUATE están completados. Esta versión puede publicarse como candidata para Etapa 2.'
            :'La versión no cumple la regla mínima de elegibilidad.'}</p></div>
      <strong className={active?'stage2-production-badge':'stage2-eligibility-badge'}>
        {active?'✓ Publicado para Etapa 2':status?.eligible?'Elegible':'No disponible'}
      </strong>
    </header>
    <div className="stage2-publication-grid">
      <span>Regla<strong>TRAIN completed + EVALUATE completed</strong></span>
      <span>TRAIN<strong>{value(status?.training_run_id)} · {value(status?.train_status)}</strong></span>
      <span>EVALUATE<strong>{value(status?.evaluation_run_id)} · {value(status?.evaluation_status)}</strong></span>
      <span>EXPLAIN<strong>{explainCount?`${explainCount} asociado(s) · informativo`:'No registrado · opcional'}</strong></span>
      <span>Versión del modelo<strong>{value(status?.model_version_id)}</strong></span>
      <span>Modelo<strong>{value(status?.model_name)}</strong></span>
      <span>Estado de publicación<strong>{active?'Activa para nuevos trabajos':status?.eligible?'Disponible para publicar':'No disponible'}</strong></span>
      {status?.publication?<><span>Publicación<strong>{status.publication.id}</strong></span>
        <span>Publicado<strong>{date(status.publication.published_at)} · {value(status.publication.published_by)}</strong></span></>:null}
    </div>
    {!status?.eligible?<p className="stage2-missing-condition" role="status">
      {status?.eligibility?.missing_conditions.join(' · ')||'Estado no elegible.'}
    </p>:null}
    <p className="stage2-experimental-warning">
      La publicación no valida checkpoint, checksum, threshold, mapping, preprocessing, framework ni forma de entrada. Esas comprobaciones se ejecutan al iniciar la inferencia. No constituye aprobación clínica ni diagnóstico automatizado.
    </p>
    {error?<p className="stage2-publication-error" role="alert">{error}</p>:null}
    {confirm?<div className="stage2-inline-confirmation" role="alert">
      <p>{confirm==='publish'
        ?'Se publicará la referencia de esta versión en el catálogo de Etapa 2. Su compatibilidad técnica se comprobará al ejecutar cada inferencia.'
        :'Los análisis anteriores conservarán su trazabilidad. El modelo dejará de estar disponible únicamente para nuevos trabajos de Etapa 2.'}</p>
      <div><button className={confirm==='publish'?'primary-action':''} disabled={loading}
        onClick={()=>void execute()} type="button">{confirm==='publish'?'Confirmar publicación':'Confirmar baja'}</button>
        <button disabled={loading} onClick={()=>setConfirm(null)} type="button">Cancelar</button></div>
    </div>:canPublish?<button className={active?'':'primary-action'} disabled={loading}
      onClick={()=>setConfirm(active?'deactivate':'publish')} type="button">
      {active?'Dar de baja de Etapa 2':'Publicar para Etapa 2'}
    </button>:<button disabled title={status?.eligibility?.missing_conditions.join(', ')}
      type="button">Publicar para Etapa 2</button>}
  </section>;
}
