import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { Loading } from '../components/Loading';
import { ApiError, api } from '../services/api';
import { isValidPublicId, routes } from '../router';
import type { CampaignListItem } from '../types/campaign';

// SWV2.3: report of the campaigns created through the configuration page. It only lists
// campaigns and links to "Nueva Campaña" / "Editar" on the configuration page; it never
// executes (execution stays a manual console command, as in SWV2.2).

interface CampaignsReportProps {
  datasource: string;
  go: (pathname: string, extra?: Record<string, string | null | undefined>) => void;
}

const number = new Intl.NumberFormat('es-CL');
const STATE_LABELS: Record<string, string> = {
  draft: 'Borrador',
  frozen: 'Congelada',
  active: 'Activa',
  paused: 'Pausada',
  finalized: 'Finalizada',
};
const EXPERIMENT_STATE_LABELS: Record<string, string> = {
  pending: 'pendiente',
  active: 'activo',
  completed: 'completado',
  failed: 'fallido',
  interrupted: 'interrompido',
  verified: 'verificado',
  excluded: 'excluido',
};

function errorCode(error: unknown) {
  if (error instanceof ApiError) {
    try {
      const body = JSON.parse(error.message) as { error?: { details?: { code?: string } } };
      return body.error?.details?.code ?? error.code ?? error.message;
    } catch {
      return error.code ?? error.message;
    }
  }
  return error instanceof Error ? error.message : 'Error desconocido.';
}

function formatTimestamp(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' })
    + ' ' + date.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });
}

function experimentsByStates(item: CampaignListItem) {
  const parts = Object.entries(item.members_by_state)
    .map(([state, count]) => `${number.format(count)} ${EXPERIMENT_STATE_LABELS[state] ?? state}${count === 1 ? '' : 's'}`);
  return parts.length ? parts.join(' · ') : '—';
}

export function CampaignsReport({ go }: CampaignsReportProps) {
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<CampaignListItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const editingId = searchParams.get('campaignId');
  const highlightId = isValidPublicId(editingId) ? editingId : null;

  const load = useCallback(() => {
    setLoading(true);
    setLoadError(null);
    api.getCampaigns({ limit: 200 })
      .then((body) => setItems(body.items))
      .catch((error) => setLoadError(errorCode(error)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  const startNewCampaign = () => go(routes.campaign);
  const editCampaign = (item: CampaignListItem) => go(routes.campaign, { campaignId: item.campaign_id });

  return <section className="page campaign-report-page">
    <div className="page-title">
      <div>
        <h1>Campañas</h1>
        <p>Reporte de las campañas experimentales creadas: dataset, modelos, Total de Experimentos y estado.</p>
      </div>
      <button type="button" className="campaign-primary" onClick={startNewCampaign}>Nueva Campaña</button>
    </div>

    {loadError ? <div className="panel warning-panel">
      <h2>No fue posible cargar el reporte de campañas</h2>
      <p>{loadError}</p>
      <button type="button" onClick={load}>Reintentar</button>
    </div> : null}

    {!loadError && loading ? <Loading /> : null}

    {!loadError && !loading && items?.length === 0 ? <div className="panel empty-state campaign-report-empty">
      <h2>No hay campañas creadas todavía</h2>
      <p>Crea la primera campaña: define dataset, modelos, optimizadores, semillas y protocolo científico.</p>
      <button type="button" className="campaign-primary" onClick={startNewCampaign}>Nueva Campaña</button>
    </div> : null}

    {!loadError && !loading && items && items.length > 0 ? <div className="panel campaign-report">
      <div className="campaign-report-row campaign-report-head" aria-hidden="true">
        <span>Campaña</span>
        <span>Estado</span>
        <span>Dataset</span>
        <span>Modelos</span>
        <span>Total de Experimentos</span>
        <span>Experimentos por estado</span>
        <span>Congelada</span>
        <span></span>
      </div>
      {items.map((item) => <div key={item.campaign_id}
        className={`campaign-report-row ${highlightId === item.campaign_id ? 'is-highlight' : ''}`}>
        <span className="campaign-report-name" data-label="Campaña">
          <strong title={item.name}>{item.name}</strong>
          <small title={item.purpose}>{item.purpose}</small>
        </span>
        <span data-label="Estado"><span className={`campaign-state-badge is-${item.state}`}>{STATE_LABELS[item.state] ?? item.state}</span></span>
        <span className="campaign-report-dataset" data-label="Dataset">
          <strong>{item.dataset_name ?? '—'}</strong>
          <small>v{item.dataset_semantic_version ?? '?'} · <code title={item.dataset_version_id}>{item.dataset_version_id.slice(0, 8)}…</code></small>
        </span>
        <span data-label="Modelos">
          <strong>{number.format(item.models.length)}</strong>
          <small title={item.models.join(', ')}>{item.models.join(', ')}</small>
        </span>
        <span data-label="Total de Experimentos">
          <strong>{number.format(item.total_experiments)}</strong>
          <small>{item.optimizers.length} optimizadores · {item.seeds.length} semillas</small>
        </span>
        <span data-label="Experimentos"><small title={experimentsByStates(item)}>{experimentsByStates(item)}</small></span>
        <span className="campaign-report-frozen" data-label="Congelada">
          <small title={item.frozen_at ?? undefined}>{formatTimestamp(item.frozen_at)}</small>
          <small><code title={item.contract_hash ?? undefined}>
            {item.contract_hash ? `${item.contract_hash.slice(0, 12)}…` : '—'}
          </code></small>
        </span>
        <span data-label="Acciones"><button type="button" className="campaign-secondary" onClick={() => editCampaign(item)}>Editar</button></span>
      </div>)}
    </div> : null}

    {!loadError && !loading && items && items.length > 0 ? <p className="api-note">
      Las campañas FROZEN son inmutables: «Editar» recarga la configuración y, si la modificas, al guardar
      se crea una nueva campaña derivada. La ejecución se inicia manualmente desde la consola.
    </p> : null}
  </section>;
}
