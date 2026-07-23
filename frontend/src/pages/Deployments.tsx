import { useEffect,useMemo,useState } from 'react';
import { ActiveProductionModel } from '../components/deployments/ActiveProductionModel';
import { ActiveStage2Model } from '../components/deployments/ActiveStage2Model';
import { DeploymentReviewPanel } from '../components/deployments/DeploymentReviewPanel';
import { ProductionActivationModal } from '../components/deployments/ProductionActivationModal';
import { TechnicalContractModal } from '../components/deployments/TechnicalContractModal';
import { ModelApprovalModal } from '../components/deployments/ModelApprovalModal';
import { Stage2EnablementModal } from '../components/stage2/Stage2EnablementModal';
import { DataTable,type Column } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { StatusBadge } from '../components/StatusBadge';
import { DEFAULT_DATASET_IMAGE_PAGE_SIZE } from '../config/pagination';
import { api } from '../services/api';
import type { DeploymentReadiness,DeploymentRow,ModelProductionReadiness,Stage2Availability } from '../types/api';
import { formatDate,formatMetric } from '../utils/format';

const short=(value:string)=>`${value.slice(0,8)}…`;
const identity=(row:DeploymentRow)=>`${row.model_name??'Modelo no identificado'}${row.version_number?` · v${row.version_number}`:''}`;
const priority=(row:DeploymentRow)=>row.environment==='production'&&row.status==='pending'?0:row.environment==='production'&&row.status==='active'?1:
  ['staging','experimental'].includes(row.environment)&&row.status==='pending'?2:row.status==='active'?3:row.status==='inactive'?4:5;

interface Props{datasource:string;selectedDeploymentId:string|null;onExecutions:()=>void;onModelVersionSelect:(id:string)=>void;onAnalysis:()=>void}
export function Deployments({datasource,selectedDeploymentId,onExecutions,onModelVersionSelect,onAnalysis}:Props){
  const[rows,setRows]=useState<DeploymentRow[]>([]);const[loading,setLoading]=useState(true);const[error,setError]=useState<string|null>(null);
  const[selectedId,setSelectedId]=useState<string|null>(selectedDeploymentId);const[readiness,setReadiness]=useState<DeploymentReadiness|null>(null);
  const[workflow,setWorkflow]=useState<ModelProductionReadiness|null>(null);
  const[stage2Availability,setStage2Availability]=useState<Stage2Availability|null>(null);
  const[stage2Modal,setStage2Modal]=useState(false);
  const[readinessLoading,setReadinessLoading]=useState(false);const[actor,setActor]=useState('operador-web');
  const[reason,setReason]=useState('Operación aprobada desde interfaz');const[sourceImageId,setSourceImageId]=useState('');
  const[rollbackTarget,setRollbackTarget]=useState('');const[busy,setBusy]=useState(false);const[notice,setNotice]=useState<string|null>(null);
  const[productionModal,setProductionModal]=useState(false);
  const[publicationProgress,setPublicationProgress]=useState<string[]>([]);
  const[contractModal,setContractModal]=useState(false);const[approvalModal,setApprovalModal]=useState(false);

  const refresh=async()=>{setLoading(true);setError(null);try{const[deployments,images]=await Promise.all([api.getDeployments(datasource),api.getDatasetImages(datasource,{page:1,page_size:DEFAULT_DATASET_IMAGE_PAGE_SIZE})]);
    setRows(deployments.items);if(!sourceImageId&&images.items[0])setSourceImageId(images.items[0].image_id);
  }catch(e){const detail=e instanceof Error?e.message:String(e);console.error('No fue posible cargar Despliegues',e);setError(detail.includes('page_size')?'No fue posible cargar los despliegues debido a una configuración de paginación inválida.':'No fue posible cargar los despliegues. Intenta nuevamente.');}finally{setLoading(false);}};
  const loadReadiness=async(id:string,clearNotice=true)=>{setReadiness(null);setWorkflow(null);setStage2Availability(null);setReadinessLoading(true);if(clearNotice)setNotice(null);
    try{const row=rows.find(item=>item.id===id)??(await api.getDeployments(datasource)).items.find(item=>item.id===id);
      if(!row)throw new Error('Deployment no encontrado.');
      const[nextReadiness,nextWorkflow,nextStage2]=await Promise.all([
        api.getDeploymentReadiness(datasource,id),
        api.getModelProductionReadiness(datasource,row.model_version_id),
        api.getTechnicalProductionPreview(datasource,row.model_version_id),
      ]);
      setReadiness(nextReadiness);setWorkflow(nextWorkflow);setStage2Availability(nextStage2);
    }catch(e){setNotice(`No fue posible evaluar el deployment. ${e instanceof Error?e.message:String(e)}`);}finally{setReadinessLoading(false);}};
  const reveal=(id:string)=>requestAnimationFrame(()=>document.getElementById(`deployment-review-${id}`)?.scrollIntoView({behavior:'smooth',block:'nearest'}));
  const toggleDeployment=async(id:string)=>{if(selectedId===id){setSelectedId(null);setReadiness(null);setWorkflow(null);setNotice(null);return;}setSelectedId(id);await loadReadiness(id);reveal(id);};

  useEffect(()=>{void refresh();},[datasource]);
  useEffect(()=>{if(selectedDeploymentId){setSelectedId(selectedDeploymentId);void loadReadiness(selectedDeploymentId).then(()=>reveal(selectedDeploymentId));}},[selectedDeploymentId,datasource]);
  useEffect(()=>{if(selectedId&&rows.some(row=>row.id===selectedId))reveal(selectedId);},[rows,selectedId]);
  const selected=selectedId?rows.find(row=>row.id===selectedId)??null:null;
  const sorted=useMemo(()=>[...rows].sort((a,b)=>priority(a)-priority(b)||String(b.created_at??'').localeCompare(String(a.created_at??''))),[rows]);
  const pending=sorted.filter(row=>row.status==='pending');const active=sorted.filter(row=>row.status==='active');const history=sorted.filter(row=>!['pending','active'].includes(row.status));
  const activeProduction=rows.find(row=>row.environment==='production'&&row.status==='active'&&row.alias==='champion'
    &&row.metadata?.production_scope!=='stage2_technical')??null;
  const activeStage2=rows.find(row=>row.environment==='production'&&row.status==='active'&&row.alias==='champion'
    &&row.metadata?.production_scope==='stage2_technical')??null;
  const currentChampion=rows.find(row=>row.id!==selectedId&&row.environment==='production'&&row.status==='active'&&row.alias==='champion')??null;

  const completeAction=async(id:string,message:string)=>{await refresh();await loadReadiness(id,false);setSelectedId(id);setNotice(message);reveal(id);};
  const act=async(action:'smoke'|'activate'|'deactivate'|'retire'|'rollback',confirmProduction=false)=>{if(!selected)return;setBusy(true);setNotice(null);
    try{if(action==='smoke'){if(!sourceImageId)throw new Error('No existe una imagen controlada.');const result=await api.smokeTestDeployment(datasource,selected.id,sourceImageId,actor);
        const passed=result.smoke_test.status==='PASS';await completeAction(selected.id,passed?`Validación aprobada. ${identity(selected)} está listo para activarse en ${selected.environment}.`:`La validación de ${identity(selected)} falló. Revise los requisitos indicados.`);}
      else if(action==='activate'){await api.activateDeployment(datasource,selected.id,actor,confirmProduction);setProductionModal(false);await completeAction(selected.id,`${identity(selected)} está activo en ${selected.environment} como ${selected.alias}.`);}
      else if(action==='rollback'){if(!rollbackTarget)throw new Error('Seleccione una revisión histórica objetivo.');const revision=await api.rollbackDeployment(datasource,selected.id,rollbackTarget,actor,reason);await completeAction(revision.id,`Rollback pendiente creado para ${identity(selected)}. Debe validarse antes de activarlo.`);}
      else{await api.transitionDeployment(datasource,selected.id,action,actor,reason);await completeAction(selected.id,action==='deactivate'?`${identity(selected)} fue desactivado.`:`${identity(selected)} fue retirado.`);}
    }catch(e){setNotice(`No fue posible completar la operación. ${e instanceof Error?e.message:String(e)}`);}finally{setBusy(false);}};
  const requestActivation=()=>{if(!selected||!readiness?.can_activate)return;if(selected.environment==='production')setProductionModal(true);else void act('activate',false);};
  const thresholdProfile=()=>selected?.threshold_calibration_id??workflow?.contract.fields.find(field=>field.key==='threshold_profile_id')?.proposed_source_id??null;
  const completeContract=async(selections:Record<string,string>)=>{if(!selected)return;setBusy(true);setNotice(null);
    try{await api.completeModelVersionContract(datasource,selected.model_version_id,selections,actor,reason);setContractModal(false);
      await completeAction(selected.id,`Contrato técnico de ${identity(selected)} completado correctamente.`);
    }catch(e){setNotice(`No fue posible completar el contrato técnico. ${e instanceof Error?e.message:String(e)}`);}finally{setBusy(false);}};
  const validateVersion=async()=>{if(!selected)return;const threshold=thresholdProfile();if(!threshold){setNotice('Falta seleccionar un threshold clínico versionado compatible.');return;}setBusy(true);
    try{await api.validateModelVersion(datasource,selected.model_version_id,threshold,actor,reason);await completeAction(selected.id,`${identity(selected)} fue validado técnica y clínicamente.`);}
    catch(e){setNotice(`No fue posible validar ${identity(selected)}. ${e instanceof Error?e.message:String(e)}`);}finally{setBusy(false);}};
  const approveVersion=async()=>{if(!selected)return;setBusy(true);
    try{await api.approveModelVersion(datasource,selected.model_version_id,actor,reason);setApprovalModal(false);await completeAction(selected.id,`${identity(selected)} fue aprobado para promoción a producción.`);}
    catch(e){setNotice(`No fue posible aprobar ${identity(selected)}. ${e instanceof Error?e.message:String(e)}`);}finally{setBusy(false);}};
  const publishToProduction=async()=>{if(!selected||!sourceImageId)return;setBusy(true);setNotice(`Se está publicando ${identity(selected)} en producción.`);
    setPublicationProgress(['Preparando deployment','Verificando artefacto','Cargando modelo','Ejecutando smoke test','Activando champion','Verificando disponibilidad','Ejecutando inferencia de control']);
    try{
      const result=await api.publishModelVersionToProduction(datasource,selected.model_version_id,{deployment_name:'malaria-classifier',alias:'champion',actor,reason,confirm_production:true,source_image_id:sourceImageId});
      if(result.status!=='active'||result.smoke_status!=='PASS'||!result.available_for_inference)throw new Error('La verificación productiva no terminó en PASS.');
      setProductionModal(false);setSelectedId(result.deployment_id);
      await completeAction(result.deployment_id,`${identity(selected)} está activo en producción como champion y disponible para análisis.`);
    }catch(e){setProductionModal(false);setNotice(`No fue posible promover ${identity(selected)}. El champion actual continúa activo. ${e instanceof Error?e.message:String(e)}`);}finally{setBusy(false);}};
  const enableStage2=async(actorValue:string,reasonValue:string)=>{if(!selected)return;setBusy(true);
    try{const result=await api.publishTechnicalProduction(datasource,selected.model_version_id,{actor:actorValue,reason:reasonValue,
      confirm_publication:true,source_image_id:sourceImageId||undefined});
      setStage2Modal(false);await refresh();setSelectedId(result.deployment_id);
      await loadReadiness(result.deployment_id,false);
      setNotice(`${identity(selected)} está activo como modelo productivo de Etapa 2. Su model_version y SHA-256 permanecen inmutables.`);
      reveal(result.deployment_id);
    }catch(e){setNotice(`No fue posible habilitar Etapa 2. ${e instanceof Error?e.message:String(e)}`);}
    finally{setBusy(false);}};
  const primaryAction=()=>{if(!workflow||!selected)return;
    if(workflow.next_action==='build_production_model_version'){setContractModal(true);return;}
    if(workflow.next_action==='validate_model_version'){void validateVersion();return;}
    if(workflow.next_action==='approve_model_version'){setApprovalModal(true);return;}
    if(workflow.next_action==='publish_to_production'){setProductionModal(true);return;}
    if(workflow.next_action==='view_production_model'&&workflow.deployment_id){setSelectedId(workflow.deployment_id);void loadReadiness(workflow.deployment_id);}
  };

  const columns:Column<DeploymentRow>[]=[
    {header:'Modelo / deployment',render:r=><><strong>{identity(r)}</strong><br/><span>{r.deployment_name}</span><br/><code>{short(r.id)}</code></>},
    {header:'Destino',render:r=><><strong>{r.environment}</strong><br/><span>{r.alias}</span></>},
    {header:'Estado',render:r=><StatusBadge status={r.status}/>},{header:'Smoke',render:r=>String((r.metadata?.smoke_test as Record<string,unknown>|undefined)?.status??'PENDIENTE')},
    {header:'Threshold',render:r=>formatMetric(r.threshold_value)},{header:'Activación',render:r=>formatDate(r.deployed_at)},
    {header:'Acción',render:r=><button className="table-action" aria-expanded={selectedId===r.id} aria-controls={`deployment-review-${r.id}`} onClick={()=>toggleDeployment(r.id)}>{selectedId===r.id?'Cerrar revisión':'Revisar despliegue'}</button>},
  ];
  const renderPanel=(row:DeploymentRow)=><DeploymentReviewPanel deployment={row} readiness={selectedId===row.id?readiness:null} readinessLoading={selectedId===row.id&&readinessLoading}
    actor={actor} reason={reason} sourceImageId={sourceImageId} rollbackTarget={rollbackTarget} busy={busy} notice={selectedId===row.id?notice:null} allDeployments={rows} workflow={selectedId===row.id?workflow:null}
    stage2Availability={selectedId===row.id?stage2Availability:null}
    onActor={setActor} onReason={setReason} onSourceImage={setSourceImageId} onRollbackTarget={setRollbackTarget} onSmoke={()=>act('smoke')} onRequestActivation={requestActivation}
    onDeactivate={()=>act('deactivate')} onRetire={()=>act('retire')} onRollback={()=>act('rollback')} onModelVersionSelect={onModelVersionSelect} onExecutions={onExecutions} onAnalysis={onAnalysis} onPrimaryAction={primaryAction}
    onBuild={()=>setContractModal(true)} onValidate={()=>void validateVersion()} onApprove={()=>setApprovalModal(true)} onPublish={()=>setProductionModal(true)}
    onEnableStage2={()=>setStage2Modal(true)} onViewStage2={(id)=>{setSelectedId(id);void loadReadiness(id).then(()=>reveal(id));}}/>;
  const table=(items:DeploymentRow[],empty:string)=><DataTable rows={items} columns={columns} emptyText={empty} getRowKey={row=>row.id} expandedRowKey={selectedId}
    renderExpandedRow={renderPanel} getRowClassName={row=>selectedId===row.id?'deployment-row deployment-row--selected':'deployment-row'} tableClassName="deployment-table" expandedRowIdPrefix="deployment-review"/>;

  if(loading&&!rows.length)return <div className="page"><Loading/></div>;
  if(error)return <div className="page"><div className="panel warning-panel"><h1>Error al cargar deployments</h1><p>{error}</p><button onClick={refresh}>Reintentar</button></div></div>;
  return <section className="page"><div className="page-title"><div><h1>Despliegues</h1><p>Revisa cada modelo en contexto, valida sus requisitos y activa una revisión gobernada.</p></div></div>
    <ActiveProductionModel deployment={activeProduction} onReview={toggleDeployment}/>
    <ActiveStage2Model deployment={activeStage2} onReview={toggleDeployment}/>
    <section className="deployment-group"><h2>Pendientes de activación</h2>{table(pending,'No existen deployments pendientes.')}</section>
    <section className="deployment-group"><h2>Activos</h2>{table(active,'No existen deployments activos.')}</section>
    <section className="deployment-group"><h2>Historial</h2>{table(history,'No existen deployments históricos.')}</section>
    {contractModal&&workflow?<TechnicalContractModal contract={workflow.contract} busy={busy} onCancel={()=>setContractModal(false)} onSave={completeContract}/>:null}
    {approvalModal&&selected&&workflow?<ModelApprovalModal identity={identity(selected)} trainingRunId={workflow.contract.training_run_id}
      evaluationRunId={workflow.contract.production_package.evaluation_run_ids[0]??null} threshold={selected.threshold_value??null}
      actor={actor} reason={reason} busy={busy} onActor={setActor} onReason={setReason} onCancel={()=>setApprovalModal(false)} onConfirm={approveVersion}/>:null}
    {productionModal&&selected&&readiness?<ProductionActivationModal deployment={selected} readiness={readiness} currentChampion={currentChampion} busy={busy}
      actor={actor} reason={reason} progress={publicationProgress} onActor={setActor} onReason={setReason}
      onCancel={()=>setProductionModal(false)} onConfirm={publishToProduction}/>:null}
    {stage2Modal&&stage2Availability?<Stage2EnablementModal preview={stage2Availability} busy={busy} mode="technical-production"
      onClose={()=>setStage2Modal(false)} onConfirm={enableStage2}/>:null}
  </section>;
}
