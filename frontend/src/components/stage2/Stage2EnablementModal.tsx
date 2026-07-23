import type { Stage2Availability } from '../../types/api';

export function Stage2EnablementModal({preview,busy,onClose,onConfirm,mode='stage2'}:{
  preview:Stage2Availability;busy:boolean;onClose:()=>void;
  onConfirm:(actor:string,reason:string)=>void;
  mode?:'stage2'|'technical-production';
}) {
  const contract=preview.package;const artifact=contract?.production_package;
  const technicalProduction=mode==='technical-production';
  return <div className="modal-backdrop" role="presentation">
    <section aria-labelledby="stage2-title" aria-modal="true" className="modal-card stage2-modal" role="dialog">
      <header><div><span className="stage2-kicker">Disponibilidad técnica</span><h2 id="stage2-title">{technicalProduction?`Publicar ${contract?.model_name??'modelo'} como modelo productivo`:'Habilitar para Etapa 2'}</h2></div>
        <button disabled={busy} onClick={onClose} type="button">Cerrar</button></header>
      <div className="stage2-warning"><strong>No constituye validación clínica ni autorización sanitaria.</strong>
        <span>El modelo quedará disponible en {technicalProduction?'production/champion con scope técnico de Etapa 2':'stage2/default'}.</span></div>
      <dl className="stage2-facts">
        <div><dt>Training Run ID</dt><dd>{preview.training_run_id}</dd></div>
        <div><dt>Model version</dt><dd>{preview.model_version_id}</dd></div>
        <div><dt>SHA-256</dt><dd>{artifact?.artifact_sha256??'No resuelto'}</dd></div>
        <div><dt>Framework</dt><dd>{artifact?.framework??'No registrado'}</dd></div>
      </dl>
      {preview.warnings.length?<div className="stage2-warnings"><strong>Advertencias</strong><ul>{preview.warnings.map(item=><li key={item}>{item}</li>)}</ul></div>:null}
      <form onSubmit={(event)=>{event.preventDefault();const data=new FormData(event.currentTarget);
        onConfirm(String(data.get('actor')||''),String(data.get('reason')||''));}}>
        <label>Responsable<input name="actor" required defaultValue="operator-web"/></label>
        <label>Motivo<textarea name="reason" required defaultValue={technicalProduction?'Modelo seleccionado para iniciar Etapa 2':'Disponibilidad técnica para Etapa 2'}/></label>
        <label className="stage2-confirm"><input name="confirm" required type="checkbox"/>Confirmo que deseo dejar este modelo disponible como productivo para la Etapa 2.</label>
        <footer><button disabled={busy} onClick={onClose} type="button">Cancelar</button>
          <button className="primary" disabled={busy} type="submit">{busy?'Copiando, verificando y publicando…':technicalProduction?'Crear versión inmutable y publicar':'Habilitar modelo'}</button></footer>
      </form>
    </section>
  </div>;
}
