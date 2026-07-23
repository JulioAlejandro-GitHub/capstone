import type { DeploymentRow } from '../../types/api';
import { formatDate,formatMetric } from '../../utils/format';
import { StatusBadge } from '../StatusBadge';

export function ActiveStage2Model({deployment,onReview}:{deployment:DeploymentRow|null;onReview:(id:string)=>void}){
  return <section className="panel active-production active-stage2" aria-labelledby="active-stage2-title">
    <div className="section-heading"><div><span className="stage2-kicker">Operación Etapa 2</span>
      <h2 id="active-stage2-title">Modelo productivo para Etapa 2</h2>
      <p>Único modelo que resuelve el selector técnico mediante production/champion.</p></div>
      {deployment?<><span className="immutable-badge">🔒 Inmutable</span><StatusBadge status={deployment.status}/></>:null}</div>
    {deployment?<div className="facts-grid">
      <span>Modelo<strong>{deployment.model_name??'No identificado'}{deployment.version_number?` · v${deployment.version_number}`:''}</strong></span>
      <span>Model version<strong>{deployment.model_version_id}</strong></span>
      <span>Deployment<strong>{deployment.id}</strong></span>
      <span>Destino<strong>production / champion</strong></span>
      <span>Scope<strong>Etapa 2 técnica · no clínica</strong></span>
      <span>Threshold operativo<strong>{formatMetric(deployment.threshold_value)}</strong></span>
      <span>Activado<strong>{formatDate(deployment.deployed_at)}</strong></span>
      <span>Integridad<strong>SHA-256 verificado</strong></span>
      <span>Acción<strong><button className="table-action" onClick={()=>onReview(deployment.id)}>Revisar modelo Etapa 2</button></strong></span>
    </div>:<div className="empty-state production-empty">No existe un modelo activo para Etapa 2.</div>}
  </section>;
}
