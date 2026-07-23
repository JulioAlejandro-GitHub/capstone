export function ModelApprovalModal({identity,trainingRunId,evaluationRunId,threshold,actor,reason,busy,onActor,onReason,onCancel,onConfirm}:{identity:string;trainingRunId:string;evaluationRunId:string|null;threshold:number|null;actor:string;reason:string;busy:boolean;onActor:(value:string)=>void;onReason:(value:string)=>void;onCancel:()=>void;onConfirm:()=>void}){
  return <div className="modal-backdrop"><div className="production-modal" role="dialog" aria-modal="true" aria-labelledby="approval-title">
    <h2 id="approval-title">Aprobar versión para producción</h2><p>La aprobación de <strong>{identity}</strong> es explícita y quedará auditada. Autoriza su publicación, pero todavía no cambiará el modelo activo.</p>
    <dl className="modal-facts"><div><dt>Training run</dt><dd>{trainingRunId.slice(0,8)}…</dd></div><div><dt>Evaluación</dt><dd>{evaluationRunId?`${evaluationRunId.slice(0,8)}…`:'No asociada'}</dd></div><div><dt>Threshold</dt><dd>{threshold??'No registrado'}</dd></div></dl>
    <div className="filters-grid"><label>Responsable<input value={actor} onChange={event=>onActor(event.target.value)}/></label><label>Motivo<textarea value={reason} onChange={event=>onReason(event.target.value)}/></label></div>
    <div className="modal-actions"><button onClick={onCancel} disabled={busy}>Cancelar</button><button className="primary-action" onClick={onConfirm} disabled={busy||!actor.trim()||!reason.trim()}>{busy?'Aprobando…':'Confirmar aprobación'}</button></div>
  </div></div>;
}
