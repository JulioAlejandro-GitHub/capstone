import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { CopyCanonicalLink } from '../components/RouteState';
import { Stage2EnablementModal } from '../components/stage2/Stage2EnablementModal';
import { Loading } from '../components/Loading';
import { isValidPublicId, routes, withAllowedQuery } from '../router';
import { api } from '../services/api';
import type { Stage2Availability } from '../types/api';

export function Stage2ReleaseDetail({ datasource }: { datasource: string }) {
  const { trainingRunId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<Stage2Availability | null>(null);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valid = isValidPublicId(trainingRunId);
  const load = async () => {
    if (!valid) return;
    setLoading(true); setError(null);
    try { setStatus(await api.getStage2ReleaseStatus(datasource, trainingRunId)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, [datasource, trainingRunId]);
  useEffect(() => {
    document.title = `Liberación Etapa 2 | ML Dashboard`;
  }, []);
  if (!valid) return <section className="page"><div className="panel warning-panel"><h1>Identificador inválido</h1><Link to={withAllowedQuery(routes.runs,{datasource})}>Volver a Ejecuciones</Link></div></section>;
  if (loading) return <div className="page"><Loading /></div>;
  if (error || !status) return <section className="page"><div className="panel warning-panel"><h1>No se pudo cargar la liberación</h1><p>{error}</p><button onClick={load}>Reintentar</button></div></section>;
  if (status.deployment_id) {
    return <section className="page"><div className="panel stage2-release-detail"><h1>Productivo Etapa 2</h1>
      <p>Este TRAIN ya tiene un deployment productivo activo.</p>
      <Link className="button-link" to={withAllowedQuery(routes.deploymentDetail(status.deployment_id),{datasource})}>Ver deployment</Link>
    </div></section>;
  }
  const publish = async (actor:string,reason:string) => {
    setPublishing(true); setError(null);
    try {
      const result = await api.publishTrainingStage2(datasource, trainingRunId, {
        actor, reason, confirm_publication: true,
      });
      setConfirming(false);
      navigate(withAllowedQuery(routes.deploymentDetail(result.deployment_id), { datasource }));
    } catch (reason) {
      setConfirming(false);
      setError(`No fue posible activar el modelo. El modelo productivo anterior continúa activo. ${reason instanceof Error ? reason.message : String(reason)}`);
      await load();
    } finally { setPublishing(false); }
  };
  const canPublish = status.eligible && status.next_action === 'enable_for_stage2';
  return <section className="page">
    <div className="page-title"><div><h1>Liberación para Etapa 2</h1><p>Publicación técnica de una versión inmutable; no constituye aprobación clínica.</p></div>
      <CopyCanonicalLink pathname={routes.runReleaseDetail(trainingRunId)} datasource={datasource}/></div>
    <div className="panel stage2-release-detail">
      <div className="facts-grid">
        <span>Training run<strong>{trainingRunId}</strong></span>
        <span>TRAIN<strong>{status.train_status ?? 'No disponible'}</strong></span>
        <span>Evaluation utilizada<strong>{status.evaluation_run_id ?? 'No asociada'}</strong></span>
        <span>EVALUATE<strong>{status.evaluation_status ?? 'No disponible'}</strong></span>
        <span>EXPLAIN<strong>{status.explainability_run_ids?.length ?? 0} asociados · opcional</strong></span>
        <span>Model version<strong>{status.model_version_id ?? 'Pendiente de preparación'}</strong></span>
        <span>Destino<strong>production / champion</strong></span>
        <span>Scope<strong>stage2_technical</strong></span>
      </div>
      {status.eligible ? <div className="deployment-readiness deployment-readiness--ready" role="status">
        <div><strong>TRAIN y EVALUATE completados</strong><p>El modelo puede publicarse para Etapa 2.</p></div><span>Elegible</span>
      </div> : <div className="warning-panel" role="status"><strong>No se puede publicar</strong><p>Se requiere un TRAIN completado y un EVALUATE completado asociado.</p></div>}
      {status.technical_blockers?.length ? <div className="warning-panel"><strong>Preparación técnica pendiente</strong>
        <ul>{status.technical_blockers.map((item)=><li key={item.code}>{item.message}</li>)}</ul></div> : null}
      {error ? <div className="warning-panel" role="alert">{error}</div> : null}
      <div className="detail-actions">
        <button className="primary-action" disabled={!canPublish || publishing} onClick={()=>setConfirming(true)}>
          {publishing ? 'Publicando…' : canPublish ? 'Publicar para Etapa 2' : 'No se puede publicar'}
        </button>
        <Link className="button-link" to={withAllowedQuery(routes.runs,{datasource})}>Volver a Ejecuciones</Link>
      </div>
    </div>
    {confirming ? <Stage2EnablementModal preview={status} busy={publishing} mode="technical-production"
      onClose={()=>setConfirming(false)} onConfirm={publish}/> : null}
  </section>;
}
