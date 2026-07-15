import { useEffect, useState } from 'react';

import { ClinicalMetricsCards } from '../components/ClinicalMetricsCards';
import { ConfusionMatrix } from '../components/ConfusionMatrix';
import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type {
  ArtifactRow,
  ExplainabilityCase,
  JsonRecord,
  RunArtifact,
  RunClinicalSummary,
  RunDetailResponse,
  RunImagePrediction,
} from '../types/api';
import { explanationImagePath, scorePositive, sourceImagePath, thresholdUsed } from '../utils/explainability';
import { formatDate, formatMetric, stringifyJson } from '../utils/format';

interface RunDetailProps {
  datasource: string;
  runId: string | null;
  onExplainabilitySelect?: (item: ExplainabilityCase) => void;
}

type PredictionFilters = {
  split: string;
  caseType: string;
  className: string;
  correct: string;
};

const IMAGE_EXTENSIONS = /\.(png|jpe?g|webp)$/i;
const SERVED_IMAGE_MIME_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp']);

function stringValue(value: unknown) {
  return typeof value === 'string' ? value : null;
}

function isImageArtifact(artifact: ArtifactRow | RunArtifact) {
  const mimeType = artifact.mime_type?.toLowerCase() ?? '';
  const path = artifactPath(artifact)?.toLowerCase() ?? '';
  const name = stringValue(artifact.name)?.toLowerCase() ?? '';

  return (
    SERVED_IMAGE_MIME_TYPES.has(mimeType)
    || IMAGE_EXTENSIONS.test(path)
    || IMAGE_EXTENSIONS.test(name)
  );
}

function artifactPath(artifact: ArtifactRow | RunArtifact) {
  return stringValue(('path' in artifact ? artifact.path : null) ?? artifact.artifact_path);
}

function isCombinedTrainingCurvesArtifact(artifact: ArtifactRow | RunArtifact) {
  if ('exists' in artifact && artifact.exists === false) return false;

  const path = artifactPath(artifact);
  const name = stringValue(artifact.name);
  return [path, name].some((value) => (
    value?.split(/[\\/]/).pop()?.toLowerCase() === 'combined_training_curves.png'
  ));
}

function booleanText(value: boolean | null | undefined) {
  if (value === true) return 'Si';
  if (value === false) return 'No';
  return '-';
}

function caseTypeLabel(caseType: string | null | undefined) {
  const labels: Record<string, string> = {
    true_positive: 'Verdadero positivo',
    true_negative: 'Verdadero negativo',
    false_positive: 'Falso positivo',
    false_negative: 'Falso negativo',
    low_confidence: 'Baja confianza',
  };
  return caseType ? labels[caseType] ?? caseType : '-';
}

function warningItems(clinical: RunClinicalSummary | null) {
  if (!clinical) return [];
  const warnings = [];
  if (clinical.clinical_metrics.prediction_collapse_detected) {
    warnings.push('Prediction collapse detectado: revisar distribucion de predicciones.');
  }
  if (clinical.checkpoint_policy.policy_satisfied === false) {
    warnings.push('La politica de checkpoint no fue satisfecha.');
  }
  if (clinical.clinical_threshold.target_recall_satisfied === false) {
    warnings.push('El target recall no fue satisfecho en validation.');
  }
  if (!clinical.clinical_threshold.enabled) {
    warnings.push('No hay threshold clinico calibrado registrado para este run.');
  }
  const threshold = clinical.clinical_threshold.threshold_used;
  if (threshold !== null && threshold !== undefined && threshold < 0.1) {
    warnings.push('Threshold muy bajo: revisar trade-off de falsos positivos.');
  }
  if (clinical.checkpoint_policy.warning) warnings.push(String(clinical.checkpoint_policy.warning));
  if (clinical.clinical_threshold.warning) warnings.push(String(clinical.clinical_threshold.warning));
  return warnings;
}

function metricFromRun(run: JsonRecord, name: string) {
  const value = run[name];
  return typeof value === 'number' ? value : null;
}

export function RunDetail({ datasource, runId, onExplainabilitySelect }: RunDetailProps) {
  const [detail, setDetail] = useState<RunDetailResponse | null>(null);
  const [clinical, setClinical] = useState<RunClinicalSummary | null>(null);
  const [confusion, setConfusion] = useState<JsonRecord[]>([]);
  const [report, setReport] = useState<JsonRecord[]>([]);
  const [artifacts, setArtifacts] = useState<RunArtifact[]>([]);
  const [imagePredictions, setImagePredictions] = useState<RunImagePrediction[]>([]);
  const [imagePredictionTotal, setImagePredictionTotal] = useState(0);
  const [explainability, setExplainability] = useState<ExplainabilityCase[]>([]);
  const [predictionFilters, setPredictionFilters] = useState<PredictionFilters>({
    split: '',
    caseType: '',
    className: '',
    correct: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [predictionsError, setPredictionsError] = useState<string | null>(null);
  const [trainingCurvesLoadFailed, setTrainingCurvesLoadFailed] = useState(false);

  useEffect(() => {
    if (!runId) return;
    setError(null);
    setDetail(null);
    setClinical(null);
    setTrainingCurvesLoadFailed(false);

    Promise.all([
      api.getRun(datasource, runId),
      api.getConfusionMatrix(datasource, runId),
      api.getClassificationReport(datasource, runId),
      api.getRunClinicalSummary(datasource, runId),
      api.getRunArtifactsSummary(datasource, runId),
      api.getRunExplainability(datasource, runId, { limit: 50 }),
    ])
      .then(([runResponse, confusionResponse, reportResponse, clinicalResponse, artifactResponse, explainabilityResponse]) => {
        setDetail(runResponse);
        setConfusion(confusionResponse.items);
        setReport(reportResponse.items);
        setClinical(clinicalResponse);
        setArtifacts(artifactResponse.items);
        setExplainability(explainabilityResponse.items);
      })
      .catch((err: Error) => setError(err.message));
  }, [datasource, runId]);

  useEffect(() => {
    if (!runId) return;
    setPredictionsError(null);
    api
      .getRunImagePredictions(datasource, runId, {
        split: predictionFilters.split || undefined,
        case_type: predictionFilters.caseType || undefined,
        class_name: predictionFilters.className || undefined,
        is_correct: predictionFilters.correct || undefined,
        limit: 100,
        offset: 0,
      })
      .then((response) => {
        setImagePredictions(response.items);
        setImagePredictionTotal(response.total);
      })
      .catch((err: Error) => setPredictionsError(err.message));
  }, [datasource, runId, predictionFilters]);

  if (!runId) return <section className="panel">Selecciona una ejecucion.</section>;
  if (error) return <section className="panel error">{error}</section>;
  if (!detail) return <Loading />;

  const run = detail.run;
  const warnings = warningItems(clinical);
  const mergedArtifacts = artifacts.length > 0 ? artifacts : detail.artifacts;
  const trainingCurvesArtifact = mergedArtifacts.find(isCombinedTrainingCurvesArtifact);
  const trainingCurvesPath = trainingCurvesArtifact ? artifactPath(trainingCurvesArtifact) : null;
  const trainingCurvesUrl = trainingCurvesArtifact && trainingCurvesPath
    ? api.artifactUrl(trainingCurvesPath, {
        artifactId: typeof trainingCurvesArtifact.id === 'string' ? trainingCurvesArtifact.id : undefined,
        datasource,
      })
    : null;
  const clinicalMetrics = clinical?.clinical_metrics ?? {
    accuracy: metricFromRun(run, 'accuracy'),
    recall_parasitized: metricFromRun(run, 'recall'),
    precision_parasitized: metricFromRun(run, 'precision'),
  };

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>{String(run.run_name ?? run.id)}</h1>
          <p>{String(run.model_name ?? clinical?.model_name ?? '-')} / {String(run.dataset_name ?? '-')}</p>
        </div>
        <StatusBadge status={String(run.status ?? clinical?.status ?? 'unknown')} />
      </div>

      <section className="panel clinical-disclaimer">
        <strong>Sistema experimental de apoyo</strong>
        <p>
          Este sistema esta destinado a apoyar el analisis de imagenes. No reemplaza la
          validacion de especialistas ni constituye diagnostico clinico definitivo.
        </p>
        <p>
          Convencion: 0 = uninfected, 1 = parasitized; raw_model_score =
          probability_parasitized.
        </p>
      </section>

      {warnings.length > 0 ? (
        <section className="panel warning-panel">
          <h2>Alertas de auditoria</h2>
          <ul>
            {warnings.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="metrics-grid">
        <div className="metric-card"><span>Tipo</span><strong>{String(run.run_type ?? clinical?.run_type ?? '-')}</strong></div>
        <div className="metric-card"><span>Script</span><strong>{String(run.script_name ?? clinical?.script_name ?? '-')}</strong></div>
        <div className="metric-card"><span>Inicio</span><strong>{formatDate(String(run.started_at ?? clinical?.started_at ?? ''))}</strong></div>
        <div className="metric-card"><span>Duracion</span><strong>{formatMetric(run.duration_seconds as number | null)} s</strong></div>
        <div className="metric-card"><span>Artefactos</span><strong>{clinical?.artifacts_count ?? detail.artifacts.length}</strong></div>
        <div className="metric-card"><span>Predicciones imagen</span><strong>{clinical?.image_predictions_count ?? imagePredictionTotal}</strong></div>
      </div>

      <section className="panel">
        <div className="section-heading">
          <h2>Metricas clinicas</h2>
          <span>Clase positiva: parasitized = 1</span>
        </div>
        <ClinicalMetricsCards metrics={clinicalMetrics} />
      </section>

      <div className="grid-two">
        <section className="panel">
          <h2>Checkpoint policy</h2>
          <div className="facts-grid">
            <span>Policy <strong>{clinical?.checkpoint_policy.policy ?? '-'}</strong></span>
            <span>Min recall requerido <strong>{formatMetric(clinical?.checkpoint_policy.min_recall_required)}</strong></span>
            <span>Epoch seleccionado <strong>{clinical?.checkpoint_policy.selected_epoch ?? '-'}</strong></span>
            <span>Policy satisfied <strong>{booleanText(clinical?.checkpoint_policy.policy_satisfied)}</strong></span>
            <span>Selected metric <strong>{clinical?.checkpoint_policy.selected_metric ?? '-'}</strong></span>
            <span>Selected value <strong>{formatMetric(clinical?.checkpoint_policy.selected_metric_value)}</strong></span>
          </div>
          {clinical?.checkpoint_policy.warning ? (
            <p className="error-text">{clinical.checkpoint_policy.warning}</p>
          ) : null}
        </section>

        <section className="panel">
          <h2>Threshold clinico</h2>
          <div className="facts-grid">
            <span>Threshold usado <strong>{formatMetric(clinical?.clinical_threshold.threshold_used)}</strong></span>
            <span>Threshold seleccionado <strong>{formatMetric(clinical?.clinical_threshold.threshold_selected)}</strong></span>
            <span>Threshold source <strong>{clinical?.clinical_threshold.threshold_source ?? '-'}</strong></span>
            <span>Target recall <strong>{formatMetric(clinical?.clinical_threshold.target_recall)}</strong></span>
            <span>Target satisfied <strong>{booleanText(clinical?.clinical_threshold.target_recall_satisfied)}</strong></span>
            <span>Validation specificity <strong>{formatMetric(clinical?.clinical_threshold.validation_specificity_at_threshold)}</strong></span>
            <span>Default threshold <strong>{formatMetric(clinical?.clinical_threshold.default_threshold)}</strong></span>
          </div>
          <p className="muted-text">El threshold clinico se calibra usando validation, no test.</p>
          {clinical?.clinical_threshold.warning ? (
            <p className="error-text">{clinical.clinical_threshold.warning}</p>
          ) : null}
        </section>
      </div>

      <section className="panel">
        <h2>Matriz de confusion clinica</h2>
        <ConfusionMatrix confusionMatrix={clinical?.confusion_matrix} />
        {clinical?.confusion_matrix.matrix?.length ? null : <pre>{stringifyJson(confusion)}</pre>}
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Predicciones por imagen</h2>
          <span>{imagePredictionTotal} registros</span>
        </div>
        <div className="filters-grid">
          <label>
            Split
            <select
              value={predictionFilters.split}
              onChange={(event) => setPredictionFilters((current) => ({ ...current, split: event.target.value }))}
            >
              <option value="">Todos</option>
              <option value="train">train</option>
              <option value="val">val</option>
              <option value="test">test</option>
              <option value="external">external</option>
            </select>
          </label>
          <label>
            Case type
            <select
              value={predictionFilters.caseType}
              onChange={(event) => setPredictionFilters((current) => ({ ...current, caseType: event.target.value }))}
            >
              <option value="">Todos</option>
              <option value="true_positive">true_positive</option>
              <option value="true_negative">true_negative</option>
              <option value="false_positive">false_positive</option>
              <option value="false_negative">false_negative</option>
              <option value="low_confidence">low_confidence</option>
            </select>
          </label>
          <label>
            Clase
            <select
              value={predictionFilters.className}
              onChange={(event) => setPredictionFilters((current) => ({ ...current, className: event.target.value }))}
            >
              <option value="">Todas</option>
              <option value="uninfected">uninfected</option>
              <option value="parasitized">parasitized</option>
            </select>
          </label>
          <label>
            Correcta
            <select
              value={predictionFilters.correct}
              onChange={(event) => setPredictionFilters((current) => ({ ...current, correct: event.target.value }))}
            >
              <option value="">Todas</option>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>
        </div>
        {predictionsError ? <p className="error-text">{predictionsError}</p> : null}
        <DataTable<RunImagePrediction>
          rows={imagePredictions}
          columns={[
            { header: 'Filename', render: (row) => row.filename ?? row.relative_path ?? '-' },
            { header: 'Split', render: (row) => row.split_name ?? '-' },
            { header: 'True label', render: (row) => row.true_label_name ?? row.true_label ?? '-' },
            { header: 'Predicted label', render: (row) => row.predicted_label_name ?? row.predicted_label ?? '-' },
            { header: 'Probability parasitized', render: (row) => formatMetric(row.probability_parasitized) },
            { header: 'Threshold', render: (row) => formatMetric(row.threshold_used) },
            {
              header: 'Case type',
              render: (row) => <span className={`case-badge ${row.case_type ?? 'unknown'}`}>{caseTypeLabel(row.case_type)}</span>,
            },
            { header: 'Correct', render: (row) => booleanText(row.is_correct) },
            {
              header: 'Imagen',
              render: (row) => row.relative_path ? (
                <a href={api.artifactUrl(row.relative_path, { datasource })} target="_blank" rel="noreferrer">Abrir</a>
              ) : '-',
            },
          ]}
          getRowKey={(row, index) => row.run_image_prediction_id ?? `${row.filename}-${index}`}
        />
      </section>

      {trainingCurvesUrl && !trainingCurvesLoadFailed ? (
        <section className="panel">
          <div className="section-heading">
            <h2>Curvas de entrenamiento</h2>
            <a href={trainingCurvesUrl} target="_blank" rel="noreferrer">Abrir imagen</a>
          </div>
          <figure className="training-curves-figure">
            <a href={trainingCurvesUrl} target="_blank" rel="noreferrer">
              <img
                src={trainingCurvesUrl}
                alt="Curvas combinadas de accuracy y loss del entrenamiento"
                onError={() => setTrainingCurvesLoadFailed(true)}
              />
            </a>
            <figcaption><code>{trainingCurvesPath}</code></figcaption>
          </figure>
        </section>
      ) : null}

      <section className="panel">
        <h2>Artefactos</h2>
        <DataTable<RunArtifact | ArtifactRow>
          rows={mergedArtifacts}
          columns={[
            { header: 'Tipo', render: (row) => row.artifact_type ?? '-' },
            {
              header: 'Path',
              render: (row) => {
                const path = artifactPath(row);
                if (!path) return '-';
                return <code>{path}</code>;
              },
            },
            { header: 'Existe', render: (row) => booleanText('exists' in row && typeof row.exists === 'boolean' ? row.exists : true) },
            { header: 'Creado', render: (row) => formatDate(String(row.created_at ?? '')) },
            {
              header: 'Abrir',
              render: (row) => {
                const path = artifactPath(row);
                if (!path) return '-';
                if (!isImageArtifact(row)) {
                  return <span className="muted-text">Vista no disponible</span>;
                }
                return (
                  <a href={api.artifactUrl(path, { artifactId: 'id' in row && typeof row.id === 'string' ? row.id : undefined, datasource })} target="_blank" rel="noreferrer">
                    Abrir imagen
                  </a>
                );
              },
            },
          ]}
          getRowKey={(row, index) => `${artifactPath(row) ?? 'artifact'}-${index}`}
        />
      </section>

      <section className="panel">
        <h2>Explicabilidad</h2>
        <p className="muted-text">Explicacion visual experimental para apoyar revision de casos, no conclusion clinica definitiva.</p>
        <DataTable<ExplainabilityCase>
          rows={explainability}
          columns={[
            {
              header: 'Fuente',
              render: (row) => {
                const path = sourceImagePath(row);
                const url = api.mediaUrl({ url: row.source_image_url ?? row.image_url, path, datasource });
                return url ? (
                  <a className="table-image-cell" href={url} target="_blank" rel="noreferrer">
                    <img src={url} alt={`Fuente ${row.true_label ?? ''}`} loading="lazy" decoding="async" />
                    <span>Abrir fuente</span>
                  </a>
                ) : <span className="muted-text">Sin fuente</span>;
              },
            },
            {
              header: 'Explicación',
              render: (row) => {
                const path = explanationImagePath(row);
                const url = api.mediaUrl({ url: row.explanation_url, path, artifactId: row.artifact_id, datasource });
                return url ? (
                  <a className="table-image-cell" href={url} target="_blank" rel="noreferrer">
                    <img src={url} alt={`Explicación ${row.method ?? ''}`} loading="lazy" decoding="async" />
                    <span>Abrir explicación</span>
                  </a>
                ) : <span className="muted-text">Sin explicación</span>;
              },
            },
            { header: 'Método', render: (row) => row.method ?? '-' },
            { header: 'Tipo de caso', render: (row) => <span className={`case-badge ${row.case_type ?? 'unknown'}`}>{caseTypeLabel(row.case_type)}</span> },
            { header: 'Clase real', render: (row) => row.true_label ?? '-' },
            { header: 'Clase predicha', render: (row) => row.predicted_label ?? '-' },
            { header: 'P(parasitized)', render: (row) => formatMetric(scorePositive(row)) },
            { header: 'Threshold', render: (row) => formatMetric(thresholdUsed(row)) },
            { header: 'Success', render: (row) => booleanText(row.success) },
            { header: 'Error', render: (row) => row.error_message ?? '-' },
            {
              header: 'Auditar',
              render: (row) => onExplainabilitySelect ? (
                <button className="audit-action-button" type="button" onClick={() => onExplainabilitySelect(row)}>Ver detalle</button>
              ) : '-',
            },
          ]}
          getRowKey={(row) => row.explainability_id}
        />
      </section>

      <section className="panel">
        <h2>Parametros de ejecucion</h2>
        <pre>{stringifyJson(run.parameters)}</pre>
      </section>

      <section className="panel">
        <h2>Metricas y reportes legacy</h2>
        <DataTable
          rows={detail.metrics}
          columns={[
            { header: 'Nombre', render: (row) => row.metric_name },
            { header: 'Valor', render: (row) => formatMetric(row.metric_value as number | null) },
            { header: 'Split', render: (row) => String(row.split_name ?? '-') },
            { header: 'Clase', render: (row) => String(row.class_name ?? '-') },
          ]}
        />
        <details>
          <summary>Reporte de clasificacion</summary>
          <pre>{stringifyJson(report)}</pre>
        </details>
      </section>
    </section>
  );
}
