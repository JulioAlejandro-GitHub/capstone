import type { Stage2Availability } from '../../types/api';

export function Stage2AvailabilityAction({status,loading,busy,error,onEnable,onView}:{
  status?:Stage2Availability;loading:boolean;busy:boolean;error?:string;
  onEnable:()=>void;onView:(deploymentId:string)=>void;
}) {
  if (status?.fixture) return <p className="run-promotion-reason">Ejecución técnica sin modelo desplegable.</p>;
  const enabled=Boolean(status&&(status.available||status.eligible)&&!busy);
  const action=()=>{
    if (!status) return;
    if (status.available&&status.deployment_id) onView(status.deployment_id);
    else onEnable();
  };
  const field=(key:string)=>status?.package?.fields.find(item=>item.key===key);
  const input=field('input_signature')?.current_value??field('input_signature')?.proposed_value;
  const preprocessing=field('preprocessing_profile_snapshot')?.current_value??field('preprocessing_profile_snapshot')?.proposed_value;
  const threshold=field('threshold_profile_id')?.current_value??field('threshold_profile_id')?.proposed_value;
  return <div className="stage2-action">
    <button className="report-detail-button stage2-action__button" disabled={!enabled||loading} onClick={action} type="button">
      {busy?'Habilitando…':loading?'Consultando…':status?.action_label??'No disponible'}
    </button>
    <span className="stage2-action__scope">Uso experimental · no clínico</span>
    {status?.eligible?<div className="stage2-action__evidence" aria-label="Evidencia técnica Etapa 2">
      <span>✓ Artefacto inmutable</span>
      <span>✓ SHA-256 verificado</span>
      <span>✓ Entrada {input&&typeof input==='object'&&'shape' in input?JSON.stringify(input.shape):'resuelta'}</span>
      <span>✓ Preprocessing {preprocessing&&typeof preprocessing==='object'&&'mode' in preprocessing?String(preprocessing.mode):'resuelto'}</span>
      <span>✓ Threshold {threshold&&typeof threshold==='object'&&'threshold' in threshold?String(threshold.threshold):'operativo'}</span>
    </div>:null}
    {status&&!status.eligible&&status.blockers.length?<details className="stage2-blockers" open>
      <summary>Por qué no está disponible</summary>
      <ul>{status.blockers.map(item=><li key={item.code}>{item.message}</li>)}</ul>
    </details>:null}
    {error?<p className="run-promotion-error" role="alert">{error}</p>:null}
  </div>;
}
