import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../auth';

import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { CaseExplainabilityView } from '../components/explainability/CaseExplainabilityView';
import { toModelExecutionExplainabilityCase } from '../components/explainability/explainabilityCaseAdapters';
import { api } from '../services/api';
import type { ExplainabilityCase, PagedResponse } from '../types/api';
import {
  caseTypeLabel,
  explanationImagePath,
  generateCaseInterpretation,
  scorePositive,
  sourceImagePath,
  thresholdUsed,
} from '../utils/explainability';
import { formatDate, formatMetric } from '../utils/format';

interface ExplainabilityProps {
  datasource: string;
  initialCase?: ExplainabilityCase | null;
  initialRunId?: string | null;
  onRunSelect?: (runId: string) => void;
}

type ExplainabilityTab =
  | 'all'
  | 'false_positive'
  | 'false_negative'
  | 'low_confidence'
  | 'true_positive'
  | 'true_negative';

type ViewMode = 'table' | 'gallery';

type Filters = {
  model_name?: string;
  dataset_name?: string;
  method?: string;
  case_type?: string;
  run_id?: string;
  true_label?: string;
  predicted_label?: string;
  threshold_source?: string;
  success?: string;
  date_from?: string;
  date_to?: string;
};

type MediaReference = {
  path: string | null;
  url: string | null;
};

const PAGE_SIZE = 48;

const tabs: Array<{ key: ExplainabilityTab; label: string }> = [
  { key: 'all', label: 'Todos los casos' },
  { key: 'false_positive', label: 'Falsos positivos' },
  { key: 'false_negative', label: 'Falsos negativos' },
  { key: 'low_confidence', label: 'Baja confianza' },
  { key: 'true_positive', label: 'Verdaderos positivos' },
  { key: 'true_negative', label: 'Verdaderos negativos' },
];

function cleanFilters(filters: Filters, activeTab: ExplainabilityTab, offset: number) {
  const params: Record<string, string | boolean | number | undefined> = {
    limit: PAGE_SIZE,
    offset,
  };

  Object.entries(filters).forEach(([key, value]) => {
    if (!value || (key === 'case_type' && activeTab !== 'all')) return;
    params[key] = key === 'success' ? value === 'true' : value;
  });

  if (activeTab !== 'all') params.case_type = activeTab;
  return params;
}

function sourceReference(item: ExplainabilityCase, datasource: string): MediaReference {
  const path = sourceImagePath(item);
  const explicitUrl = item.source_image_url
    ?? (!item.source_image_path && !item.image_stored_path && !item.original_image_path
      ? item.image_url
      : null);
  return {
    path,
    url: api.mediaUrl({ url: explicitUrl, path, datasource }),
  };
}

function explanationReference(item: ExplainabilityCase, datasource: string): MediaReference {
  const path = explanationImagePath(item);
  return {
    path,
    url: api.mediaUrl({
      url: item.explanation_url,
      path,
      artifactId: item.artifact_id,
      datasource,
    }),
  };
}

function caseDate(item: ExplainabilityCase) {
  return item.started_at ?? item.created_at ?? item.uploaded_at ?? null;
}

function methodLabel(method: string | null | undefined) {
  if (!method) return '-';
  if (method.toLowerCase() === 'gradcam') return 'Grad-CAM';
  return method.toUpperCase();
}

function ImageWithFallback({
  reference,
  alt,
  compact = false,
  emptyText,
}: {
  reference: MediaReference;
  alt: string;
  compact?: boolean;
  emptyText: string;
}) {
  const [failed, setFailed] = useState(false);

  useEffect(() => setFailed(false), [reference.url]);

  if (!reference.url || failed) {
    return <div className={`image-placeholder ${compact ? 'compact' : ''}`}>{failed ? 'No fue posible cargar la imagen.' : emptyText}</div>;
  }

  return <img src={reference.url} alt={alt} loading="lazy" decoding="async" onError={() => setFailed(true)} />;
}

function TableImagePreview({
  reference,
  alt,
  emptyText,
}: {
  reference: MediaReference;
  alt: string;
  emptyText: string;
}) {
  if (!reference.url) return <span className="muted-text">{emptyText}</span>;
  return (
    <a className="table-image-cell" href={reference.url} target="_blank" rel="noreferrer">
      <ImageWithFallback reference={reference} alt={alt} compact emptyText={emptyText} />
      <span>Abrir imagen</span>
    </a>
  );
}

export function CaseDetail({
  item,
  datasource,
  onClose,
  onRunSelect,
  onGenerated,
}: {
  item: ExplainabilityCase;
  datasource: string;
  onClose: () => void;
  onRunSelect?: (runId: string) => void;
  onGenerated?: (item: ExplainabilityCase) => void;
}) {
  const { user } = useAuth();
  const canGenerate = Boolean(user?.permissions.includes('scientific.cell_classification.explain'));
  return (
    <CaseExplainabilityView
      case={toModelExecutionExplainabilityCase(item, datasource)}
      onClose={onClose}
      onRunSelect={onRunSelect}
      canGenerate={canGenerate}
      onGenerate={async () => {
        const generated = await api.generateCaseGradCam(item.explainability_id);
        onGenerated?.(generated);
        return toModelExecutionExplainabilityCase(generated, datasource);
      }}
    />
  );
}

function GalleryCard({
  item,
  datasource,
  onOpen,
}: {
  item: ExplainabilityCase;
  datasource: string;
  onOpen: () => void;
}) {
  const source = sourceReference(item, datasource);
  const explanation = explanationReference(item, datasource);

  return (
    <article className={`artifact-card case-card audit-gallery-card ${item.case_type ?? 'unknown'}`}>
      <div className="case-card-header">
        <strong>{methodLabel(item.method)}</strong>
        <span className={`case-badge ${item.case_type ?? 'unknown'}`}>{caseTypeLabel(item.case_type)}</span>
      </div>
      <small>{item.model_name ?? 'Modelo sin registrar'} · {item.dataset_name ?? 'Dataset sin registrar'}</small>
      <div className="case-images">
        <div className="case-image-block">
          <span>Imagen original</span>
          {source.url ? (
            <a href={source.url} target="_blank" rel="noreferrer">
              <ImageWithFallback reference={source} alt={`Fuente original ${item.true_label ?? ''}`} emptyText="Fuente no disponible." />
            </a>
          ) : <ImageWithFallback reference={source} alt="Fuente original" emptyText="Fuente original no registrada." />}
        </div>
        <div className="case-image-block">
          <span>Explicación</span>
          {explanation.url ? (
            <a href={explanation.url} target="_blank" rel="noreferrer">
              <ImageWithFallback reference={explanation} alt={`Explicación ${methodLabel(item.method)}`} emptyText="Explicación no disponible." />
            </a>
          ) : <ImageWithFallback reference={explanation} alt="Explicación visual" emptyText="Explicación no disponible." />}
        </div>
      </div>
      <div className="case-facts">
        <span>Real <strong>{item.true_label ?? '-'}</strong></span>
        <span>Predicha <strong>{item.predicted_label ?? '-'}</strong></span>
        <span>Score <strong>{formatMetric(scorePositive(item))}</strong></span>
        <span>Threshold <strong>{formatMetric(thresholdUsed(item))}</strong></span>
      </div>
      <p className="case-interpretation">{generateCaseInterpretation(item)}</p>
      <div className="gallery-links">
        {source.url ? <a href={source.url} target="_blank" rel="noreferrer">Abrir fuente original</a> : <span>Fuente no disponible</span>}
        {explanation.url ? <a href={explanation.url} target="_blank" rel="noreferrer">Abrir explicación</a> : <span>Explicación no disponible</span>}
      </div>
      <div className="case-card-footer">
        <small>Run: {item.run_id ?? '-'}</small>
        <button className="audit-action-button" type="button" onClick={onOpen}>Ver detalle</button>
      </div>
      {item.error_message ? <p className="detail-error">{item.error_message}</p> : null}
    </article>
  );
}

export function Explainability({ datasource, initialCase = null, initialRunId = null, onRunSelect }: ExplainabilityProps) {
  const [activeTab, setActiveTab] = useState<ExplainabilityTab>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [filters, setFilters] = useState<Filters>(() => ({ run_id: initialRunId ?? undefined }));
  const [offset, setOffset] = useState(0);
  const [cases, setCases] = useState<PagedResponse<ExplainabilityCase> | null>(null);
  const [selectedCase, setSelectedCase] = useState<ExplainabilityCase | null>(initialCase);
  const [error, setError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  const params = useMemo(() => cleanFilters(filters, activeTab, offset), [filters, activeTab, offset]);

  useEffect(() => {
    setFilters((current) => {
      const nextRunId = initialRunId ?? undefined;
      return current.run_id === nextRunId ? current : { ...current, run_id: nextRunId };
    });
    setSelectedCase(initialCase ?? null);
  }, [initialCase, initialRunId]);

  useEffect(() => {
    let ignore = false;
    setError(null);
    setCases(null);

    const request = viewMode === 'gallery'
      ? api.getExplainabilityGallery(datasource, params)
      : activeTab === 'false_positive'
        ? api.getFalsePositiveCases(datasource, params)
        : activeTab === 'false_negative'
          ? api.getFalseNegativeCases(datasource, params)
          : activeTab === 'low_confidence'
            ? api.getLowConfidenceCases(datasource, params)
            : api.getExplainabilityCases(datasource, params);

    request
      .then((response) => {
        if (!ignore) setCases(response);
      })
      .catch((err: Error) => {
        if (!ignore) setError(err.message);
      });

    return () => { ignore = true; };
  }, [activeTab, datasource, params, retryToken, viewMode]);

  const updateFilter = (key: keyof Filters, value: string) => {
    setFilters((current) => ({ ...current, [key]: value || undefined }));
    setOffset(0);
  };

  const selectTab = (tab: ExplainabilityTab) => {
    setActiveTab(tab);
    setOffset(0);
  };

  const selectView = (mode: ViewMode) => {
    setViewMode(mode);
    setOffset(0);
  };

  const resetFilters = () => {
    setFilters({});
    setOffset(0);
  };

  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = cases ? Math.max(1, Math.ceil(cases.total / PAGE_SIZE)) : 1;

  return (
    <section className="page explainability-page">
      <div className="page-title explainability-title">
        <div>
          <p className="eyebrow">Auditoría parasitológica asistida</p>
          <h1>Explicabilidad caso a caso</h1>
          <p>Compare la fuente original, la decisión del modelo y el artefacto visual sin perder la trazabilidad del run.</p>
        </div>
        <div className="view-toggle" aria-label="Modo de visualización">
          <button className={viewMode === 'table' ? 'active' : ''} type="button" onClick={() => selectView('table')}>Tabla</button>
          <button className={viewMode === 'gallery' ? 'active' : ''} type="button" onClick={() => selectView('gallery')}>Galería</button>
        </div>
      </div>

      <section className="panel clinical-disclaimer audit-disclaimer">
        <strong>Explicaciones experimentales, revisión humana obligatoria</strong>
        <p>Grad-CAM, LIME y SHAP señalan regiones influyentes; no prueban causalidad ni reemplazan la evaluación de un especialista.</p>
      </section>

      <section className="panel audit-controls">
        <div className="tabs audit-tabs">
          {tabs.map((tab) => (
            <button key={tab.key} className={activeTab === tab.key ? 'active' : ''} onClick={() => selectTab(tab.key)} type="button">
              {tab.label}
            </button>
          ))}
        </div>

        <div className="filters-grid">
          <label>
            Modelo
            <input value={filters.model_name ?? ''} onChange={(event) => updateFilter('model_name', event.target.value)} placeholder="vgg16_transfer_learning" />
          </label>
          <label>
            Dataset
            <input value={filters.dataset_name ?? ''} onChange={(event) => updateFilter('dataset_name', event.target.value)} placeholder="NIH/NLM Malaria" />
          </label>
          <label>
            Método
            <select value={filters.method ?? ''} onChange={(event) => updateFilter('method', event.target.value)}>
              <option value="">Todos</option>
              <option value="gradcam">Grad-CAM</option>
              <option value="lime">LIME</option>
              <option value="shap">SHAP</option>
            </select>
          </label>
          <label>
            Tipo de caso
            <select value={activeTab === 'all' ? filters.case_type ?? '' : activeTab} onChange={(event) => updateFilter('case_type', event.target.value)} disabled={activeTab !== 'all'}>
              <option value="">Todos</option>
              <option value="true_positive">Verdadero positivo</option>
              <option value="true_negative">Verdadero negativo</option>
              <option value="false_positive">Falso positivo</option>
              <option value="false_negative">Falso negativo</option>
              <option value="low_confidence">Baja confianza</option>
            </select>
          </label>
          <label>
            Clase real
            <select value={filters.true_label ?? ''} onChange={(event) => updateFilter('true_label', event.target.value)}>
              <option value="">Todas</option>
              <option value="parasitized">parasitized</option>
              <option value="uninfected">uninfected</option>
            </select>
          </label>
          <label>
            Clase predicha
            <select value={filters.predicted_label ?? ''} onChange={(event) => updateFilter('predicted_label', event.target.value)}>
              <option value="">Todas</option>
              <option value="parasitized">parasitized</option>
              <option value="uninfected">uninfected</option>
            </select>
          </label>
          <label>
            Fuente threshold
            <input value={filters.threshold_source ?? ''} onChange={(event) => updateFilter('threshold_source', event.target.value)} placeholder="fixed_cli, calibrated…" list="threshold-sources" />
            <datalist id="threshold-sources"><option value="fixed_cli" /><option value="calibrated_validation" /><option value="run_parameter" /></datalist>
          </label>
          <label>
            Run ID
            <input value={filters.run_id ?? ''} onChange={(event) => updateFilter('run_id', event.target.value)} placeholder="UUID" />
          </label>
          <label>
            Estado
            <select value={filters.success ?? ''} onChange={(event) => updateFilter('success', event.target.value)}>
              <option value="">Todos</option>
              <option value="true">Generada</option>
              <option value="false">Fallida</option>
            </select>
          </label>
          <label>
            Desde
            <input type="date" value={filters.date_from ?? ''} onChange={(event) => updateFilter('date_from', event.target.value)} />
          </label>
          <label>
            Hasta
            <input type="date" value={filters.date_to ?? ''} onChange={(event) => updateFilter('date_to', event.target.value)} />
          </label>
        </div>
        <div className="filter-actions">
          <button type="button" onClick={resetFilters}>Limpiar filtros</button>
          <span>{cases ? `${cases.total} casos encontrados` : 'Consultando casos…'}</span>
        </div>
      </section>

      {error ? (
        <section className="panel error inline-error">
          <strong>No fue posible cargar los casos.</strong>
          <span>{error}</span>
          <button type="button" onClick={() => setRetryToken((value) => value + 1)}>Reintentar</button>
        </section>
      ) : !cases ? <Loading /> : viewMode === 'table' ? (
        <section className="panel audit-results-panel">
          <div className="section-heading">
            <h2>Casos auditables</h2>
            <span>Página {currentPage} de {totalPages}</span>
          </div>
          <DataTable<ExplainabilityCase>
            rows={cases.items}
            getRowKey={(row, index) => row.explainability_id ?? `${row.run_id ?? 'case'}-${index}`}
            emptyText="No hay explicaciones que coincidan con los filtros."
            columns={[
              { header: 'Original', render: (row) => <TableImagePreview reference={sourceReference(row, datasource)} alt="Imagen original" emptyText="Sin fuente" /> },
              { header: 'Explicación', render: (row) => <TableImagePreview reference={explanationReference(row, datasource)} alt={`Explicación ${methodLabel(row.method)}`} emptyText="Sin explicación" /> },
              { header: 'Método', render: (row) => methodLabel(row.method) },
              { header: 'Real → predicha', render: (row) => <span className="label-transition"><strong>{row.true_label ?? '-'}</strong><span>→</span><strong>{row.predicted_label ?? '-'}</strong></span> },
              { header: 'Score', render: (row) => formatMetric(scorePositive(row)) },
              { header: 'Threshold', render: (row) => <span>{formatMetric(thresholdUsed(row))}<small className="cell-subtitle">{row.threshold_source ?? '-'}</small></span> },
              { header: 'Caso', render: (row) => <span className={`case-badge ${row.case_type ?? 'unknown'}`}>{caseTypeLabel(row.case_type)}</span> },
              { header: 'Modelo / dataset', render: (row) => <span>{row.model_name ?? '-'}<small className="cell-subtitle">{row.dataset_name ?? '-'}</small></span> },
              { header: 'Run ID', render: (row) => row.run_id ? <code className="compact-code">{row.run_id}</code> : '-' },
              { header: 'Fecha', render: (row) => formatDate(caseDate(row)) },
              { header: 'Acción', render: (row) => <button className="audit-action-button" type="button" onClick={() => setSelectedCase(row)}>Ver detalle</button> },
            ]}
          />
        </section>
      ) : (
        <section className="audit-gallery-section">
          <div className="section-heading">
            <h2>Galería comparativa</h2>
            <span>Página {currentPage} de {totalPages}</span>
          </div>
          {cases.items.length ? (
            <div className="audit-gallery-grid">
              {cases.items.map((item, index) => (
                <GalleryCard key={item.explainability_id ?? `${item.run_id ?? 'case'}-${index}`} item={item} datasource={datasource} onOpen={() => setSelectedCase(item)} />
              ))}
            </div>
          ) : <div className="empty-state">No hay explicaciones que coincidan con los filtros.</div>}
        </section>
      )}

      {cases && cases.total > PAGE_SIZE ? (
        <div className="pagination-bar audit-pagination">
          <button type="button" disabled={offset === 0} onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))}>Anterior</button>
          <span>Página {currentPage} de {totalPages}</span>
          <button type="button" disabled={offset + PAGE_SIZE >= cases.total} onClick={() => setOffset((value) => value + PAGE_SIZE)}>Siguiente</button>
        </div>
      ) : null}

      {selectedCase ? (
        <CaseDetail item={selectedCase} datasource={datasource} onClose={() => setSelectedCase(null)} onRunSelect={onRunSelect} />
      ) : null}
    </section>
  );
}
