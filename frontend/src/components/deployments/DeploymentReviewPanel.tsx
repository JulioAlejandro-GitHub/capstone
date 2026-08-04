import { useEffect,useRef } from 'react';
import type { DeploymentReadiness,DeploymentRow,ModelProductionReadiness } from '../../types/api';
import { formatDate,formatMetric } from '../../utils/format';
import { Loading } from '../Loading';
import { StatusBadge } from '../StatusBadge';
import { ProductionStepIndicator } from './ProductionStepIndicator';

const short=(value:string)=>`${value.slice(0,8)}…`;
const modelIdentity=(deployment:DeploymentRow,readiness:DeploymentReadiness|null)=>`${readiness?.model_name??deployment.model_name??'Modelo no identificado'}${(readiness?.version_number??deployment.version_number)?` v${readiness?.version_number??deployment.version_number}`:''}`;
const isLegacyStage2=(deployment:DeploymentRow)=>[
  'stage2_experimental','stage2_technical',
].includes(String(deployment.metadata?.production_scope??''))
  ||(deployment.environment==='stage2'&&deployment.alias==='default');

interface Props {
  deployment:DeploymentRow;readiness:DeploymentReadiness|null;readinessLoading:boolean;
  workflow:ModelProductionReadiness|null;
  actor:string;reason:string;sourceImageId:string;rollbackTarget:string;busy:boolean;notice:string|null;
  allDeployments:DeploymentRow[];onActor:(value:string)=>void;onReason:(value:string)=>void;
  onSourceImage:(value:string)=>void;onRollbackTarget:(value:string)=>void;onSmoke:()=>void;
  onDeactivate:()=>void;onRetire:()=>void;onRollback:()=>void;
  onModelVersionSelect:(id:string)=>void;onExecutions:()=>void;onAnalysis:()=>void;
  onPrimaryAction:()=>void;
  onBuild:()=>void;onValidate:()=>void;onApprove:()=>void;onPublish:()=>void;
}

export function DeploymentReviewPanel(props:Props){
  const{deployment,readiness,readinessLoading,busy,notice}=props;const headingRef=useRef<HTMLHeadingElement>(null);
  useEffect(()=>{if(!readinessLoading)headingRef.current?.focus({preventScroll:true});},[deployment.id,readinessLoading]);
  const identity=modelIdentity(deployment,readiness);const smokeStatus=String(readiness?.smoke_test?.status??'PENDIENTE');
  const historicalStage2=isLegacyStage2(deployment);
  const trainingRunId=readiness?.training_run_id??deployment.training_run_id;
  const rollbackOptions=props.allDeployments.filter(row=>row.id!==deployment.id&&row.deployment_name===deployment.deployment_name&&row.environment===deployment.environment&&row.alias===deployment.alias);
  return <section className="deployment-inline-review" aria-live="polite" aria-labelledby={`review-title-${deployment.id}`}>
    <div className="section-heading"><div><span className="review-kicker">Está revisando</span><h2 ref={headingRef} tabIndex={-1} id={`review-title-${deployment.id}`}>{identity}</h2><p>{deployment.deployment_name}</p></div><StatusBadge status={deployment.status}/></div>
    <div className="facts-grid deployment-identity"><span>Destino<strong>{deployment.environment} / {deployment.alias}</strong></span><span>Model version<strong>{short(deployment.model_version_id)}</strong></span>
      <span>Training run<strong>{trainingRunId?short(trainingRunId):'No registrado'}</strong></span><span>Deployment<strong>{short(deployment.id)}</strong></span>
      <span>SHA-256<strong>{deployment.artifact_sha256?short(deployment.artifact_sha256):'No registrado'}</strong></span>
      <span>Artifact<strong>{historicalStage2?'Referencia histórica':'Registrado'}</strong></span>
      <span>Threshold<strong>{formatMetric(deployment.threshold_value)}</strong></span><span>Smoke<strong>{smokeStatus}</strong></span>{deployment.deployed_at?<span>Activado<strong>{formatDate(deployment.deployed_at)}</strong></span>:null}</div>
    {!readinessLoading&&props.workflow&&!historicalStage2?<ProductionStepIndicator readiness={props.workflow}/>:null}
    {historicalStage2?<div className="stage2-operational-banner">
      <div><span className="stage2-kicker">Registro histórico Etapa 2</span><strong>Consulta sin operaciones</strong>
        <p>Este deployment se conserva para trazabilidad. Las altas y bajas vigentes se administran exclusivamente desde la tarjeta TRAIN en Ejecuciones.</p></div>
      <span className="immutable-badge">Solo lectura</span>
    </div>:null}
    {!historicalStage2&&readinessLoading?<Loading/>:!historicalStage2&&readiness?<><div className={`deployment-readiness deployment-readiness--${props.workflow?.production_status.available_for_inference?'ready':'blocked'}`}>
      <div><strong>{deployment.status==='active'?`${identity} está activo en ${deployment.environment} como ${deployment.alias}.`:readiness.can_activate?'Listo para activar':'Deployment bloqueado'}</strong>
        <p>{deployment.status==='active'?'La revisión activa está disponible para las operaciones permitidas.':readiness.can_activate?'Todos los requisitos técnicos están cumplidos.':'Revise cada requisito bloqueado antes de continuar.'}</p></div>
      <span>{readiness.requirements.filter(item=>item.status==='pass').length}/{readiness.requirements.filter(item=>item.status!=='not_applicable').length} requisitos</span></div>
      <h3>Requisitos técnicos</h3><ol className="deployment-checklist">{readiness.requirements.filter(item=>item.key!=='smoke').map(item=><li key={item.key} data-status={item.status}><span aria-hidden="true">{item.status==='pass'?'✓':item.status==='blocked'?'!':'○'}</span><div><strong>{item.label}</strong><p>{item.detail}</p></div></li>)}</ol>
    </>:null}
    {notice?<div className="inline-operation-notice" role="status"><strong>Resultado</strong><p>{notice}</p></div>:null}
    {!historicalStage2?<div className="filters-grid"><label>Responsable<input value={props.actor} onChange={e=>props.onActor(e.target.value)}/></label><label>Motivo<input value={props.reason} onChange={e=>props.onReason(e.target.value)}/></label>
      {deployment.status==='active'?<label>Revisión para rollback<select value={props.rollbackTarget} onChange={e=>props.onRollbackTarget(e.target.value)}><option value="">Seleccione</option>{rollbackOptions.map(row=><option value={row.id} key={row.id}>{short(row.id)} · {row.status}</option>)}</select></label>:null}</div>:null}
    {!historicalStage2&&['pending','inactive'].includes(deployment.status)?<details className="advanced-options"><summary>Configuración avanzada del smoke test</summary><label>Imagen controlada<input value={props.sourceImageId} onChange={e=>props.onSourceImage(e.target.value)}/></label><small>Se selecciona automáticamente una imagen registrada.</small></details>:null}
    {props.workflow&&!historicalStage2?<div className="deployment-flow-actions four-step-actions">
      <div><span>Paso 1 — Versión inmutable y contrato técnico</span><strong>{props.workflow.contract.contract_complete?'Completo':props.workflow.contract.can_complete_contract?'Listo para completar':'Bloqueado'}</strong><button disabled={busy||props.workflow.contract.contract_complete||!props.workflow.can_build_package} title={!props.workflow.can_build_package?'Falta evidencia inequívoca o la versión ya es inmutable.':undefined} onClick={props.onBuild}>{props.workflow.contract.status==='discovered'?'Completar versión productiva':'Generar versión productiva'}</button></div>
      <div><span>Paso 2 — Validación</span><strong>{['validated','approved','deployed'].includes(deployment.model_version_status??'')?'Completa':props.workflow.can_validate?'Disponible':'Pendiente'}</strong><button disabled={busy||!props.workflow.can_validate} title={!props.workflow.can_validate?'Complete primero la versión productiva.':undefined} onClick={props.onValidate}>Validar versión</button></div>
      <div><span>Paso 3 — Aprobación</span><strong>{['approved','deployed'].includes(deployment.model_version_status??'')?'Completa':props.workflow.can_approve?'Disponible':'Pendiente'}</strong><button disabled={busy||!props.workflow.can_approve} title={!props.workflow.can_approve?'La versión debe estar validated.':undefined} onClick={props.onApprove}>Aprobar versión</button></div>
      <div><span>Paso 4 — Publicación en producción</span><strong>{props.workflow.production_status.available_for_inference?'Activa':props.workflow.can_publish?'Disponible':'Bloqueada'}</strong><small>Incluye deployment production, smoke test, champion e inferencia de control.</small><button disabled={busy||!props.workflow.can_publish||props.workflow.is_active_in_production} title={!props.workflow.can_publish?(props.workflow.production_blockers?.join(' · ')||'La versión no cumple los requisitos productivos.'):undefined} onClick={props.onPublish}>Publicar en producción</button></div>
    </div>:null}
    {props.workflow&&!historicalStage2&&!props.workflow.contract.contract_complete?<div className="panel warning-panel contract-blocker">
      <strong>Contrato técnico incompleto</strong>
      <p>{props.workflow.contract.immutable_reason??'Complete los campos con evidencia inequívoca antes de validar.'}</p>
      {props.workflow.contract.fields.filter(field=>!['complete','ready'].includes(field.status)).map(field=><p key={field.key}><strong>{field.label}:</strong> faltante o ambiguo. Fuentes buscadas: {field.sources_searched.join(', ')}.</p>)}
      {props.workflow.contract.artifact_inspection_error?<p>{props.workflow.contract.artifact_inspection_error}</p>:null}
    </div>:null}
    {!historicalStage2&&props.workflow?.production_blockers?.length?<div className="panel warning-panel contract-blocker" role="alert">
      <strong>No se puede publicar este modelo en producción</strong>
      {props.workflow.production_blockers.map(reason=><p key={reason}>{reason}</p>)}
      <p>El champion actual continuará activo. Prepare una model_version nueva desde un entrenamiento real si esta versión es una fixture técnica.</p>
    </div>:null}
    {props.workflow&&!historicalStage2?<button className="primary-action deployment-next-action" disabled={busy||(
      (props.workflow.next_action==='build_production_model_version'&&!props.workflow.can_build_package)
      ||props.workflow.next_action==='production_blocked'
    )} onClick={props.onPrimaryAction}>{busy?'Procesando…':props.workflow.action_label}</button>:null}
    <div className="detail-actions">{historicalStage2?<>
      <button onClick={()=>props.onModelVersionSelect(deployment.model_version_id)}>Revisar modelo liberado</button>
      <button onClick={props.onExecutions}>Ir a la publicación vigente</button>
    </>:<>
      {deployment.status==='active'?<button onClick={props.onAnalysis}>Ir a análisis</button>:null}
      {deployment.status==='active'?<button disabled={busy} onClick={props.onDeactivate}>Desactivar</button>:null}
      {deployment.status==='active'?<button disabled={busy||!props.rollbackTarget||!props.reason.trim()} onClick={props.onRollback}>Crear rollback pendiente</button>:null}
      {deployment.status!=='retired'?<button disabled={busy} onClick={props.onRetire}>Retirar</button>:null}
      {readiness&&!readiness.can_run_smoke?<button onClick={()=>props.onModelVersionSelect(deployment.model_version_id)}>Revisar modelo liberado</button>:null}
      <button onClick={props.onExecutions}>Volver a Ejecuciones</button>
    </>}</div>
    {!historicalStage2&&readiness&&!readiness.can_run_smoke&&deployment.status==='pending'?<p className="api-note">Complete los snapshots indicados en la model version o prepare una nueva versión liberable desde Ejecuciones.</p>:null}
  </section>;
}
