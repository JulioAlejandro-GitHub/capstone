import type { DeploymentRow } from '../../types/api';
import { formatDate,formatMetric } from '../../utils/format';
import { StatusBadge } from '../StatusBadge';

export function ActiveProductionModel({deployment,onReview}:{deployment:DeploymentRow|null;onReview:(id:string)=>void}){
  return <section className="panel active-production" aria-labelledby="active-production-title"><div className="section-heading"><div><h2 id="active-production-title">Modelo activo en producción</h2><p>Champion utilizado por el selector de análisis.</p></div>{deployment?<StatusBadge status={deployment.status}/>:null}</div>
    {deployment?<div className="facts-grid"><span>Modelo<strong>{deployment.model_name??'No identificado'}{deployment.version_number?` · v${deployment.version_number}`:''}</strong></span><span>Deployment<strong>{deployment.deployment_name}</strong></span><span>Alias<strong>{deployment.alias}</strong></span><span>Threshold<strong>{formatMetric(deployment.threshold_value)}</strong></span><span>Activado<strong>{formatDate(deployment.deployed_at)}</strong></span><span>Acción<strong><button className="table-action" onClick={()=>onReview(deployment.id)}>Revisar deployment</button></strong></span></div>:<div className="empty-state production-empty">No existe un modelo activo en producción.</div>}
  </section>;
}
