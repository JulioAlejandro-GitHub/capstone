import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useSmearAnalysisHistoryDetail } from '../hooks/useSmearAnalysisHistoryDetail';
import { routes } from '../router';
import {
  api,
  type SmearAnalysisHistoryItem,
  type SmearAnalysisHistoryPage,
} from '../services/api';
import { SmearAnalysisReadOnlyView } from './SmearWorkflow';

const PAGE_SIZE = 25;
const emptyPage: SmearAnalysisHistoryPage = {
  items: [],
  total: 0,
  limit: PAGE_SIZE,
  offset: 0,
};
const emptyFilters = {
  run_code: '',
  subject_code: '',
  sample_code: '',
  status: '',
  quality_gate_status: '',
  ready_for_analysis: '',
  created_from: '',
  created_to: '',
};

const statusLabels: Record<string, string> = {
  created: 'Cargado',
  quality_pending: 'Control pendiente',
  queued: 'En cola',
  quality_processing: 'Procesando calidad',
  review_required: 'Advertencia pendiente',
  blocked: 'Bloqueado por calidad',
  ready_for_analysis: 'Listo para detección',
  processing: 'Detectando células',
  completed: 'Completado',
  completed_with_warnings: 'Completado con advertencias',
  failed: 'Fallido',
  cancelled: 'Fallido',
};
const label = (value: string | null | undefined) =>
  value ? statusLabels[value] ?? value.replaceAll('_', ' ') : 'Sin registro';
const safeDate = (value: string | null | undefined) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
};

function HistoryRow({ item }: { item: SmearAnalysisHistoryItem }) {
  const reviewTotal = item.detection_count;
  return (
    <tr>
      <td data-label="Análisis"><strong>{item.run_code}</strong><small>{item.image_count} imagen(es)</small></td>
      <td data-label="Paciente / muestra"><strong>{item.subject_code}</strong><small>{item.sample_code} · {item.slide_code}</small></td>
      <td data-label="Creación"><time dateTime={item.created_at}>{safeDate(item.created_at)}</time><small>Fin: {safeDate(item.completed_at)}</small></td>
      <td data-label="Estado"><span className={`history-status status-${item.analysis_status}`}>{label(item.analysis_status)}</span><small>Calidad: {label(item.quality_gate_status)}</small></td>
      <td data-label="Detección"><strong>{label(item.detection_status)}</strong><small>{item.detection_count} detecciones</small></td>
      <td data-label="Revisión"><strong>{item.reviewed_count} / {reviewTotal}</strong><small>células revisadas</small></td>
      <td data-label="Solicitante"><span>{item.requested_by_username}</span></td>
      <td data-label="Acción"><Link className="history-detail-link" to={routes.smearHistoryDetail(item.analysis_run_id)}>Ver detalle</Link></td>
    </tr>
  );
}

export function SmearAnalysisHistory() {
  const [draft, setDraft] = useState(emptyFilters);
  const [filters, setFilters] = useState(emptyFilters);
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState(emptyPage);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const query = useMemo(() => ({
    ...Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== '')),
    limit: PAGE_SIZE,
    offset,
  }), [filters, offset]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    api.getSmearAnalysisHistory(query)
      .then((response) => {
        if (active) setPage(response);
      })
      .catch(() => {
        if (active) setError('No fue posible consultar el historial de análisis.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [query]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setOffset(0);
    setFilters(draft);
  };
  const clear = () => {
    setDraft(emptyFilters);
    setFilters(emptyFilters);
    setOffset(0);
  };
  const hasFilters = Object.values(filters).some(Boolean);

  return (
    <section className="page smear-history-page">
      <header className="smear-history-header">
        <div><p className="workflow-kicker">Análisis de frotis</p><h1>Historial de análisis</h1><p>Consulta trazable de ejecuciones persistidas.</p></div>
        <strong>{page.total} resultado(s)</strong>
      </header>
      <form className="smear-history-filters" onSubmit={submit}>
        <label>Run<input value={draft.run_code} onChange={(event) => setDraft({ ...draft, run_code: event.target.value })} /></label>
        <label>Paciente<input value={draft.subject_code} onChange={(event) => setDraft({ ...draft, subject_code: event.target.value })} /></label>
        <label>Muestra<input value={draft.sample_code} onChange={(event) => setDraft({ ...draft, sample_code: event.target.value })} /></label>
        <label>Estado<select value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}><option value="">Todos</option><option value="quality_pending">Control pendiente</option><option value="review_required">Advertencia pendiente</option><option value="blocked">Bloqueado</option><option value="ready_for_analysis">Listo para detección</option><option value="failed">Fallido</option></select></label>
        <label>Calidad<select value={draft.quality_gate_status} onChange={(event) => setDraft({ ...draft, quality_gate_status: event.target.value })}><option value="">Todas</option><option value="pending">Pendiente</option><option value="pass">Aprobada</option><option value="warning">Advertencia</option><option value="fail">Fallida</option><option value="error">Error</option></select></label>
        <label>Preparado<select value={draft.ready_for_analysis} onChange={(event) => setDraft({ ...draft, ready_for_analysis: event.target.value })}><option value="">Todos</option><option value="true">Sí</option><option value="false">No</option></select></label>
        <label>Desde<input type="date" value={draft.created_from} onChange={(event) => setDraft({ ...draft, created_from: event.target.value })} /></label>
        <label>Hasta<input type="date" value={draft.created_to} onChange={(event) => setDraft({ ...draft, created_to: event.target.value })} /></label>
        <div className="smear-history-filter-actions"><button type="submit">Aplicar filtros</button><button type="button" onClick={clear}>Limpiar filtros</button></div>
      </form>

      {error ? <p className="smear-history-message" role="alert">{error}</p> : null}
      {loading ? <p className="smear-history-message" role="status">Consultando análisis persistidos…</p> : null}
      {!loading && !error && !page.items.length ? (
        <p className="smear-history-message">{hasFilters ? 'No hay análisis que coincidan con los filtros' : 'No existen análisis registrados'}</p>
      ) : null}
      {!loading && page.items.length ? (
        <div className="smear-history-table-wrap">
          <table className="smear-history-table">
            <thead><tr><th>Análisis</th><th>Paciente / muestra</th><th>Fechas</th><th>Estado</th><th>Detección</th><th>Revisión</th><th>Solicitante</th><th>Acción</th></tr></thead>
            <tbody>{page.items.map((item) => <HistoryRow key={item.analysis_run_id} item={item} />)}</tbody>
          </table>
        </div>
      ) : null}
      <nav className="smear-history-pagination" aria-label="Paginación del historial">
        <button type="button" disabled={loading || offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Anterior</button>
        <span>{page.total ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, page.total)} de ${page.total}` : '0 resultados'}</span>
        <button type="button" disabled={loading || offset + PAGE_SIZE >= page.total} onClick={() => setOffset(offset + PAGE_SIZE)}>Siguiente</button>
      </nav>
    </section>
  );
}

export function SmearAnalysisHistoryDetail({ analysisRunId }: { analysisRunId: string }) {
  const navigate = useNavigate();
  const { data, loading, error } = useSmearAnalysisHistoryDetail(analysisRunId);
  if (loading) return <section className="page smear-history-message" role="status">Recuperando análisis histórico…</section>;
  if (error || !data) return <section className="page smear-history-error" role="alert"><h1>Análisis no disponible</h1><p>{error}</p><button type="button" onClick={() => navigate(routes.smearHistory)}>Volver al historial</button></section>;
  return <SmearAnalysisReadOnlyView workflow={data} onBack={() => navigate(routes.smearHistory)} />;
}
