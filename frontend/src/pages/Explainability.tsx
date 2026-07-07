import { useEffect, useMemo, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { api } from '../services/api';
import type { ExplainabilityCase, ExplainabilityCaseSummary, PagedResponse } from '../types/api';
import { formatDate, formatMetric } from '../utils/format';

interface ExplainabilityProps {
  datasource: string;
}

type ExplainabilityTab = 'all' | 'false_positive' | 'false_negative' | 'low_confidence' | 'summary';

type Filters = {
  model_name?: string;
  dataset_name?: string;
  method?: string;
  case_type?: string;
  run_id?: string;
  true_label?: string;
  predicted_label?: string;
  success?: string;
};

const tabs: Array<{ key: ExplainabilityTab; label: string }> = [
  { key: 'all', label: 'Todos los casos' },
  { key: 'false_positive', label: 'Falsos positivos' },
  { key: 'false_negative', label: 'Falsos negativos' },
  { key: 'low_confidence', label: 'Baja confianza' },
  { key: 'summary', label: 'Resumen' },
];

function cleanFilters(filters: Filters) {
  const params: Record<string, string | boolean | number | undefined> = {
    limit: 50,
    offset: 0,
  };

  Object.entries(filters).forEach(([key, value]) => {
    if (!value) return;
    if (key === 'success') {
      params.success = value === 'true';
    } else {
      params[key] = value;
    }
  });

  return params;
}

function caseTypeLabel(caseType: string | null) {
  const labels: Record<string, string> = {
    true_positive: 'Verdadero positivo',
    true_negative: 'Verdadero negativo',
    false_positive: 'Falso positivo',
    false_negative: 'Falso negativo',
    low_confidence: 'Baja confianza',
  };
  return caseType ? labels[caseType] ?? caseType : '-';
}

function generateCaseInterpretation(item: ExplainabilityCase) {
  const trueLabel = item.true_label ?? 'clase desconocida';
  const predictedLabel = item.predicted_label ?? 'clase desconocida';
  const positiveLabel = item.positive_label ?? 'parasitized';
  const score = formatMetric(item.probability_parasitized ?? item.score_positive_label);
  const method = item.method?.toUpperCase() ?? 'explicabilidad';

  if (item.case_type === 'false_positive') {
    return `La imagen estaba etiquetada como ${trueLabel}, pero el modelo la clasifico como ${positiveLabel} con score ${score}. El mapa ${method} muestra la region que mas influyo en esta decision. Este caso debe revisarse como posible confusion visual o artefacto.`;
  }
  if (item.case_type === 'false_negative') {
    return `La imagen estaba etiquetada como ${positiveLabel}, pero el modelo la clasifico como ${predictedLabel}. Este caso requiere revision prioritaria porque representa una celula parasitada no detectada por el modelo.`;
  }
  if (item.case_type === 'true_positive') {
    return `La imagen estaba etiquetada como ${positiveLabel} y el modelo tambien la clasifico como ${positiveLabel}. La explicacion visual permite revisar si la decision se apoya en una region microscopica plausible.`;
  }
  if (item.case_type === 'low_confidence') {
    return 'La prediccion esta cercana al umbral de decision. Este caso debe ser priorizado para revision humana.';
  }
  return `La imagen estaba etiquetada como ${trueLabel} y el modelo predijo ${predictedLabel} con score ${score}.`;
}

function realImagePath(item: ExplainabilityCase) {
  return item.image_path;
}

function explanationImagePath(item: ExplainabilityCase) {
  return item.explanation_output_path ?? item.artifact_path;
}

function tableImagePreview(
  path: string | null | undefined,
  alt: string,
  emptyText: string,
  datasource: string,
  artifactId?: string | null,
) {
  if (!path) {
    return <span className="muted-text">{emptyText}</span>;
  }

  const imageUrl = api.artifactUrl(path, { artifactId, datasource });
  return (
    <a className="table-image-cell" href={imageUrl} target="_blank" rel="noreferrer">
      <img src={imageUrl} alt={alt} />
      <span>Abrir imagen</span>
    </a>
  );
}

export function Explainability({ datasource }: ExplainabilityProps) {
  const [activeTab, setActiveTab] = useState<ExplainabilityTab>('all');
  const [filters, setFilters] = useState<Filters>({});
  const [cases, setCases] = useState<PagedResponse<ExplainabilityCase> | null>(null);
  const [summary, setSummary] = useState<PagedResponse<ExplainabilityCaseSummary> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const params = useMemo(() => cleanFilters(filters), [filters]);

  useEffect(() => {
    setError(null);
    setCases(null);
    setSummary(null);

    const request =
      activeTab === 'false_positive'
        ? api.getFalsePositiveCases(datasource, params)
        : activeTab === 'false_negative'
          ? api.getFalseNegativeCases(datasource, params)
          : activeTab === 'low_confidence'
            ? api.getLowConfidenceCases(datasource, params)
            : activeTab === 'summary'
              ? api.getExplainabilityCaseSummary(datasource, params)
              : api.getExplainabilityCases(datasource, params);

    request
      .then((response) => {
        if (activeTab === 'summary') {
          setSummary(response as PagedResponse<ExplainabilityCaseSummary>);
        } else {
          setCases(response as PagedResponse<ExplainabilityCase>);
        }
      })
      .catch((err: Error) => setError(err.message));
  }, [activeTab, datasource, params]);

  const updateFilter = (key: keyof Filters, value: string) => {
    setFilters((current) => ({
      ...current,
      [key]: value || undefined,
    }));
  };

  if (error) return <section className="panel error">{error}</section>;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Explicabilidad caso a caso</h1>
          <p>Revision individual de imagen, probabilidad estimada, threshold, tipo de error y artefacto visual experimental.</p>
        </div>
      </div>

      <section className="panel">
        <div className="tabs">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              className={activeTab === tab.key ? 'active' : ''}
              onClick={() => setActiveTab(tab.key)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="filters-grid">
          <label>
            Modelo
            <input
              value={filters.model_name ?? ''}
              onChange={(event) => updateFilter('model_name', event.target.value)}
              placeholder="vgg16_transfer_learning"
            />
          </label>
          <label>
            Dataset
            <input
              value={filters.dataset_name ?? ''}
              onChange={(event) => updateFilter('dataset_name', event.target.value)}
              placeholder="NIH/NLM Malaria..."
            />
          </label>
          <label>
            Metodo
            <select value={filters.method ?? ''} onChange={(event) => updateFilter('method', event.target.value)}>
              <option value="">Todos</option>
              <option value="gradcam">Grad-CAM</option>
              <option value="lime">LIME</option>
              <option value="shap">SHAP</option>
            </select>
          </label>
          <label>
            Tipo de caso
            <select
              value={filters.case_type ?? ''}
              onChange={(event) => updateFilter('case_type', event.target.value)}
            >
              <option value="">Todos</option>
              <option value="true_positive">Verdadero positivo</option>
              <option value="true_negative">Verdadero negativo</option>
              <option value="false_positive">Falso positivo</option>
              <option value="false_negative">Falso negativo</option>
              <option value="low_confidence">Baja confianza</option>
            </select>
          </label>
          <label>
            Run ID
            <input
              value={filters.run_id ?? ''}
              onChange={(event) => updateFilter('run_id', event.target.value)}
              placeholder="uuid"
            />
          </label>
          <label>
            Clase real
            <input
              value={filters.true_label ?? ''}
              onChange={(event) => updateFilter('true_label', event.target.value)}
              placeholder="parasitized"
            />
          </label>
          <label>
            Clase predicha
            <input
              value={filters.predicted_label ?? ''}
              onChange={(event) => updateFilter('predicted_label', event.target.value)}
              placeholder="uninfected"
            />
          </label>
          <label>
            Success
            <select value={filters.success ?? ''} onChange={(event) => updateFilter('success', event.target.value)}>
              <option value="">Todos</option>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>
        </div>
      </section>

      {activeTab === 'summary' ? (
        !summary ? (
          <Loading />
        ) : (
          <section className="panel">
            <h2>Resumen por tipo de caso</h2>
            <p className="result-count">Total grupos: {summary.total}</p>
            <DataTable<ExplainabilityCaseSummary>
              rows={summary.items}
              columns={[
                { header: 'Modelo', render: (row) => row.model_name ?? '-' },
                { header: 'Dataset', render: (row) => row.dataset_name ?? '-' },
                { header: 'Metodo', render: (row) => row.method ?? '-' },
                { header: 'Caso', render: (row) => caseTypeLabel(row.case_type) },
                { header: 'Total', render: (row) => row.total_cases },
                { header: 'Score prom.', render: (row) => formatMetric(row.avg_score) },
                { header: 'Min', render: (row) => formatMetric(row.min_score) },
                { header: 'Max', render: (row) => formatMetric(row.max_score) },
                { header: 'Ultimo run', render: (row) => formatDate(row.latest_run_at) },
              ]}
            />
          </section>
        )
      ) : !cases ? (
        <Loading />
      ) : (
        <>
          <section className="panel">
            <h2>Tabla detallada</h2>
            <p className="result-count">Total casos: {cases.total}</p>
            <DataTable<ExplainabilityCase>
              rows={cases.items}
              columns={[
                { header: 'Modelo', render: (row) => row.model_name ?? '-' },
                { header: 'Dataset', render: (row) => row.dataset_name ?? '-' },
                { header: 'Metodo', render: (row) => row.method },
                {
                  header: 'Caso',
                  render: (row) => <span className={`case-badge ${row.case_type ?? 'unknown'}`}>{caseTypeLabel(row.case_type)}</span>,
                },
                { header: 'Real', render: (row) => row.true_label ?? '-' },
                { header: 'Predicha', render: (row) => row.predicted_label ?? '-' },
                { header: 'Probability parasitized', render: (row) => formatMetric(row.probability_parasitized ?? row.score_positive_label) },
                { header: 'Threshold used', render: (row) => formatMetric(row.threshold_used ?? row.threshold) },
                { header: 'Threshold source', render: (row) => row.threshold_source ?? '-' },
                // {
                //   header: 'Imagen',
                //   render: (row) =>
                //     tableImagePreview(
                //       realImagePath(row),
                //       `Imagen real ${row.true_label ?? ''}`,
                //       'Sin imagen',
                //       datasource,
                //     ),
                // },

                {
                  header: 'Explicacion',
                  render: (row) =>
                    tableImagePreview(
                      explanationImagePath(row),
                      `${row.method} ${row.case_type ?? ''}`,
                      'Sin explicacion',
                      datasource,
                      row.artifact_id,
                    ),
                },
                { header: 'Capa', render: (row) => row.last_conv_layer ?? '-' },
                { header: 'Fecha', render: (row) => formatDate(row.started_at) },
              ]}
            />
          </section>

          <section className="panel">
            <h2>Galeria visual</h2>
            <div className="artifact-grid">
              {cases.items.map((item) => {
                const realPath = realImagePath(item);
                const explanationPath = explanationImagePath(item);
                return (
                  <article key={item.explainability_id} className={`artifact-card case-card ${item.case_type ?? 'unknown'}`}>
                    <div className="case-card-header">
                      <strong>{item.method}</strong>
                      <span className={`case-badge ${item.case_type ?? 'unknown'}`}>{caseTypeLabel(item.case_type)}</span>
                    </div>
                    <small>{item.model_name ?? '-'} / {item.dataset_name ?? '-'}</small>
                    <div className="">
                      {/* <div className="case-image-block">
                        <span>Imagen real</span>
                        {realPath ? (
                          <a href={api.artifactUrl(realPath, { datasource })} target="_blank" rel="noreferrer">
                            <img
                              src={api.artifactUrl(realPath, { datasource })}
                              alt={`Imagen real ${item.true_label ?? ''}`}
                            />
                          </a>
                        ) : (
                          <div className="image-placeholder">Imagen real no registrada para este caso.</div>
                        )}
                      </div> */}
                      <div className="case-image-block">
                        <span>Explicacion visual</span>
                        {explanationPath ? (
                          <a
                            href={api.artifactUrl(explanationPath, { artifactId: item.artifact_id, datasource })}
                            target="_blank"
                            rel="noreferrer"
                          >
                            <img
                              src={api.artifactUrl(explanationPath, { artifactId: item.artifact_id, datasource })}
                              alt={`${item.method} ${item.case_type}`}
                            />
                          </a>
                        ) : (
                          <div className="image-placeholder">Explicacion no disponible.</div>
                        )}
                      </div>
                    </div>
                    <div className="case-facts">
                      <span>Real: <strong>{item.true_label ?? '-'}</strong></span>
                      <span>Predicha: <strong>{item.predicted_label ?? '-'}</strong></span>
                      <span>Probability parasitized: <strong>{formatMetric(item.probability_parasitized ?? item.score_positive_label)}</strong></span>
                      <span>Threshold used: <strong>{formatMetric(item.threshold_used ?? item.threshold)}</strong></span>
                      <span>Threshold source: <strong>{item.threshold_source ?? '-'}</strong></span>
                    </div>
                    <p>{generateCaseInterpretation(item)}</p>
                    <code>{item.explanation_output_path ?? item.image_path ?? '-'}</code>
                    <small>run_id: {item.run_id}</small>
                    {item.error_message ? <p className="error-text">{item.error_message}</p> : null}
                  </article>
                );
              })}
            </div>
          </section>
        </>
      )}
    </section>
  );
}
