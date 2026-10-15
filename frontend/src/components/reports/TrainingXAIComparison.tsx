import { useEffect, useMemo, useState } from 'react';
import { useAssessment } from '../../hooks/useAssessment';
import { useAssessmentArtifacts } from '../../hooks/useAssessmentArtifacts';
import type { AssessmentExplanationChild } from '../../types/api';
import { XAIComparisonViewer } from './XAIComparisonViewer';
import { groupXAIComparisons, XAI_LABELS, XAI_METHODS, type XAIAttemptPage, type XAIMethod } from './xai/comparison';

function AttemptPage({attemptId, trainingRunId, method, onPage}: {
  attemptId: string; trainingRunId: string; method: XAIMethod;
  onPage: (method: XAIMethod, page: XAIAttemptPage | null) => void;
}) {
  const {data, loading, error} = useAssessment(attemptId);
  if (loading) return <p role="status">Cargando {XAI_LABELS[method]}…</p>;
  if (error || !data) return <p role="alert">{XAI_LABELS[method]}: {error ?? 'Intento no disponible'}</p>;
  if (data.training_run_id !== trainingRunId || data.id !== attemptId || data.kind !== 'explain' || data.identity.explanation?.method !== method) {
    return <p role="alert">No comparable: el intento no corresponde al TRAIN o método seleccionado.</p>;
  }
  return <ArtifactPage key={data.id} detail={data} method={method} onPage={onPage} />;
}

function ArtifactPage({detail, method, onPage}: {
  detail: XAIAttemptPage['detail']; method: XAIMethod;
  onPage: (method: XAIMethod, page: XAIAttemptPage | null) => void;
}) {
  const [offset, setOffset] = useState(0);
  const {items, loading, error} = useAssessmentArtifacts(detail.id, offset);
  const readyItems = !loading && !error ? items : null;
  useEffect(() => {
    onPage(method, readyItems ? {detail, artifacts: readyItems} : null);
    return () => onPage(method, null);
  }, [detail, readyItems, method, onPage]);
  return <div>
    {loading && <p role="status">Cargando referencias de {XAI_LABELS[method]}…</p>}
    {error && <p role="alert">{XAI_LABELS[method]}: {error}</p>}
    <nav className="xai-actions" aria-label={`Páginas de referencias ${XAI_LABELS[method]}`}>
      <span>{XAI_LABELS[method]} · página {offset / 100 + 1}</span>
      <button className="ds-button" type="button" disabled={loading || offset === 0} onClick={() => setOffset(value => Math.max(0, value - 100))}>Anterior</button>
      <button className="ds-button" type="button" disabled={loading || items.length < 100} onClick={() => setOffset(value => value + 100)}>Siguiente</button>
    </nav>
  </div>;
}

export function TrainingXAIComparison({assessments, trainingRunId, datasource}: {
  assessments: AssessmentExplanationChild[]; trainingRunId: string; datasource: string;
}) {
  const [choices, setChoices] = useState<Partial<Record<XAIMethod, string>>>({});
  const [pages, setPages] = useState<Partial<Record<XAIMethod, XAIAttemptPage>>>({});
  const [rowPage, setRowPage] = useState(0);
  // Stable callback avoids re-registering pages after parent renders.
  const onPage = useMemo(() => (method: XAIMethod, page: XAIAttemptPage | null) => {
    setPages(previous => {
      if (!page && !previous[method]) return previous;
      const next = {...previous};
      if (page) next[method] = page; else delete next[method];
      return next;
    });
    setRowPage(0);
  }, []);
  const selected = Object.fromEntries(XAI_METHODS.map(method => [method,
    choices[method] ?? assessments.find(item => item.method === method)?.attempt_id ?? ''])) as Record<XAIMethod, string>;
  const rows = useMemo(() => groupXAIComparisons(Object.values(pages).filter(page =>
    page && selected[page.detail.identity.explanation?.method as XAIMethod] === page.detail.id) as XAIAttemptPage[], trainingRunId),
  [pages, selected.gradcam, selected.lime, selected.shap, trainingRunId]);
  const visibleRows = rows.slice(rowPage * 5, rowPage * 5 + 5);
  return <section className="ds-report xai-comparison-browser" data-surface="workbench" aria-label="Visor XAI por muestra">
    <h3 className="ds-subsection-title">Comparación por muestra</h3>
    <p className="report-copy">Selecciona un intento por método. Solo se comparan las referencias de las páginas seleccionadas con la misma muestra, TRAIN, modelo, checkpoint y contexto de datos. Los métodos ausentes en estas páginas no implican que nunca se hayan ejecutado.</p>
    <div className="ds-dl">
      {XAI_METHODS.map(method => <label key={method}>{XAI_LABELS[method]}
        <select className="ds-control" value={selected[method]} onChange={event => { setChoices(previous => ({...previous, [method]: event.target.value})); setRowPage(0); }}>
          <option value="">Sin intento seleccionado</option>
          {assessments.filter(item => item.method === method).map(item => <option key={item.attempt_id} value={item.attempt_id}>#{item.ordinal} · {item.state} · {item.attempt_id}</option>)}
        </select>
      </label>)}
    </div>
    {XAI_METHODS.map(method => selected[method] && <AttemptPage key={selected[method]} method={method} attemptId={selected[method]}
      trainingRunId={trainingRunId} onPage={onPage} />)}
    {!rows.length && <p role="status">No hay muestras disponibles en las referencias cargadas. Consulta los estados de cada intento y su historial.</p>}
    {visibleRows.map(row => <XAIComparisonViewer key={row.id} comparison={row} datasource={datasource} />)}
    {rows.length > 0 && <nav className="xai-actions" aria-label="Páginas de muestras comparadas">
      <span>{rows.length} filas en las referencias cargadas · página {rowPage + 1} de {Math.ceil(rows.length / 5)}</span>
      <button className="ds-button" type="button" disabled={rowPage === 0} onClick={() => setRowPage(page => page - 1)}>Muestras anteriores</button>
      <button className="ds-button" type="button" disabled={(rowPage + 1) * 5 >= rows.length} onClick={() => setRowPage(page => page + 1)}>Muestras siguientes</button>
    </nav>}
  </section>;
}
