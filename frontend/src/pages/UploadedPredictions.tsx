import { useEffect, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type { AvailableModel, InferenceResult, JsonValue, PagedResponse, UploadedPrediction } from '../types/api';
import { formatDate, formatMetric } from '../utils/format';


interface UploadedPredictionsProps {
  datasource: string;
  onRunSelect: (runId: string) => void;
  onExplainabilityOpen?: (runId: string) => void;
}


function uploadedImagePath(row: UploadedPrediction) {
  return row.image_stored_path ?? row.artifact_path ?? row.image_path ?? row.original_image_path;
}

function booleanLabel(value: boolean | null | undefined) {
  if (value === true) return 'Sí';
  if (value === false) return 'No';
  return '-';
}

function qualityLabel(row: UploadedPrediction) {
  if (row.quality_passed === true) return 'Aprobada';
  if (row.quality_passed === false) return 'Observada';
  return '-';
}

function formatWarnings(value: JsonValue | null | undefined) {
  if (!value) return '-';
  if (Array.isArray(value)) {
    return value.length > 0
      ? value.map((item) => (typeof item === 'string' ? item : JSON.stringify(item))).join('; ')
      : '-';
  }
  if (typeof value === 'string') return value || '-';
  return JSON.stringify(value);
}

function calibrationLabel(row: UploadedPrediction) {
  const method = row.calibration_method ?? 'none';
  return `${method} (${row.calibration_applied ? 'aplicada' : 'no aplicada'})`;
}

function decisionLabel(row: UploadedPrediction) {
  return row.decision_code ?? row.decision ?? '-';
}

function ttaEnsembleLabel(row: UploadedPrediction) {
  const tta = booleanLabel(row.tta_applied ?? row.tta);
  const nAug = row.n_aug ? ` (${row.n_aug} aug)` : '';
  return `TTA: ${tta}${nAug} / Ensemble: ${booleanLabel(row.ensemble_applied)}`;
}


export function UploadedPredictions({ datasource, onRunSelect, onExplainabilityOpen }: UploadedPredictionsProps) {
  const [predictions, setPredictions] = useState<PagedResponse<UploadedPrediction> | null>(null);
  const [modelName, setModelName] = useState('');
  const [predictedLabel, setPredictedLabel] = useState('');
  const [qualityPassed, setQualityPassed] = useState('');
  const [calibrationMethod, setCalibrationMethod] = useState('');
  const [calibrationApplied, setCalibrationApplied] = useState('');
  const [ttaApplied, setTtaApplied] = useState('');
  const [ensembleApplied, setEnsembleApplied] = useState('');
  const [confidenceLevel, setConfidenceLevel] = useState('');
  const [caseType, setCaseType] = useState('');
  const [decisionCode, setDecisionCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [availableModels,setAvailableModels]=useState<AvailableModel[]>([]);
  const [deploymentId,setDeploymentId]=useState('');
  const [sourceImageId,setSourceImageId]=useState('');
  const [inference,setInference]=useState<InferenceResult|null>(null);
  const [inferenceBusy,setInferenceBusy]=useState(false);
  const [inferenceError,setInferenceError]=useState<string|null>(null);

  useEffect(()=>{Promise.all([api.getAvailableModels(datasource),api.getDatasetImages(datasource,{page_size:24})])
    .then(([models,images])=>{setAvailableModels(models.items);setDeploymentId(current=>current||models.items[0]?.id||'');setSourceImageId(current=>current||images.items[0]?.image_id||'');})
    .catch(err=>setInferenceError(err instanceof Error?err.message:String(err)));},[datasource]);
  const executeInference=async()=>{setInferenceBusy(true);setInferenceError(null);try{
    setInference(await api.createImageAnalysisJob(datasource,deploymentId,sourceImageId));
  }catch(err){setInferenceError(err instanceof Error?err.message:String(err));}finally{setInferenceBusy(false);}};

  useEffect(() => {
    setError(null);
    setPredictions(null);
    api
      .getUploadedPredictions(datasource, {
        model_name: modelName || undefined,
        predicted_label: predictedLabel || undefined,
        quality_passed: qualityPassed || undefined,
        calibration_method: calibrationMethod || undefined,
        calibration_applied: calibrationApplied || undefined,
        tta_applied: ttaApplied || undefined,
        ensemble_applied: ensembleApplied || undefined,
        confidence_level: confidenceLevel || undefined,
        case_type: caseType || undefined,
        decision_code: decisionCode || undefined,
        limit: 100,
      })
      .then(setPredictions)
      .catch((err: Error) => setError(err.message));
  }, [
    datasource,
    modelName,
    predictedLabel,
    qualityPassed,
    calibrationMethod,
    calibrationApplied,
    ttaApplied,
    ensembleApplied,
    confidenceLevel,
    caseType,
    decisionCode,
  ]);

  if (error) return <section className="panel error">{error}</section>;
  if (!predictions) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Inferencia clínica experimental</h1>
          <p>Imagenes externas evaluadas con src.predict_image y registradas con --track-db.</p>
        </div>
      </div>

      <section className="panel clinical-disclaimer">
        <strong>Uso experimental</strong>
        <p>
          Este reporte es una herramienta de apoyo para revision caso a caso. No reemplaza diagnostico
          clinico, validacion de laboratorio ni revision por especialistas.
        </p>
      </section>

      <section className="panel">
        <div className="section-heading"><h2>Nuevo análisis trazable</h2><span>{availableModels.length} modelos disponibles</span></div>
        <div className="filters-grid"><label>Deployment activo<select value={deploymentId} onChange={e=>setDeploymentId(e.target.value)}><option value="">Seleccione un modelo</option>{availableModels.map(model=><option key={model.id} value={model.id}>{model.model_name} v{model.version_number} · {model.environment}/{model.alias}</option>)}</select></label>
          <label>Imagen registrada<input value={sourceImageId} onChange={e=>setSourceImageId(e.target.value)}/></label>
          <button disabled={inferenceBusy||!deploymentId||!sourceImageId} onClick={executeInference}>{inferenceBusy?'Analizando…':'Ejecutar análisis'}</button></div>
        {inferenceError?<div className="warning-panel" role="alert">{inferenceError}</div>:null}
        {inference?<div className="facts-grid" role="status"><span>Resultado<strong>{inference.predicted_label} ({inference.predicted_class})</strong></span><span>Probabilidad parasitized<strong>{formatMetric(inference.probability_parasitized)}</strong></span><span>Inference run<strong>{inference.inference_run_id}</strong></span><span>Image job<strong>{inference.image_analysis_job_id}</strong></span></div>:null}
      </section>

      <section className="panel">
        <div className="filters-grid">
          <label>
            Modelo
            <input
              placeholder="custom_cnn, vgg16_transfer_learning..."
              value={modelName}
              onChange={(event) => setModelName(event.target.value)}
            />
          </label>
          <label>
            Clase predicha
            <select value={predictedLabel} onChange={(event) => setPredictedLabel(event.target.value)}>
              <option value="">Todas</option>
              <option value="parasitized">parasitized</option>
              <option value="uninfected">uninfected</option>
            </select>
          </label>
          <label>
            Calidad
            <select value={qualityPassed} onChange={(event) => setQualityPassed(event.target.value)}>
              <option value="">Todas</option>
              <option value="true">Aprobada</option>
              <option value="false">Observada</option>
            </select>
          </label>
          <label>
            Calibración
            <select value={calibrationMethod} onChange={(event) => setCalibrationMethod(event.target.value)}>
              <option value="">Todos</option>
              <option value="none">none</option>
              <option value="temperature_scaling">temperature_scaling</option>
            </select>
          </label>
          <label>
            Calibración aplicada
            <select value={calibrationApplied} onChange={(event) => setCalibrationApplied(event.target.value)}>
              <option value="">Todas</option>
              <option value="true">Sí</option>
              <option value="false">No</option>
            </select>
          </label>
          <label>
            TTA
            <select value={ttaApplied} onChange={(event) => setTtaApplied(event.target.value)}>
              <option value="">Todos</option>
              <option value="true">Sí</option>
              <option value="false">No</option>
            </select>
          </label>
          <label>
            Ensemble
            <select value={ensembleApplied} onChange={(event) => setEnsembleApplied(event.target.value)}>
              <option value="">Todos</option>
              <option value="true">Sí</option>
              <option value="false">No</option>
            </select>
          </label>
          <label>
            Confianza
            <select value={confidenceLevel} onChange={(event) => setConfidenceLevel(event.target.value)}>
              <option value="">Todas</option>
              <option value="high">high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
            </select>
          </label>
          <label>
            Caso
            <select value={caseType} onChange={(event) => setCaseType(event.target.value)}>
              <option value="">Todos</option>
              <option value="true_positive">true_positive</option>
              <option value="true_negative">true_negative</option>
              <option value="false_positive">false_positive</option>
              <option value="false_negative">false_negative</option>
              <option value="unknown">unknown</option>
            </select>
          </label>
          <label>
            Decisión
            <input
              placeholder="positive, negative, review..."
              value={decisionCode}
              onChange={(event) => setDecisionCode(event.target.value)}
            />
          </label>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Consultas registradas</h2>
          <span>{predictions.total} registros</span>
        </div>
        <DataTable<UploadedPrediction>
          rows={predictions.items}
          getRowKey={(row) => row.prediction_id}
          emptyText="No hay imagenes subidas para prediccion registradas en BD."
          columns={[
            {
              header: 'Imagen subida',
              render: (row) => {
                const path = uploadedImagePath(row);
                if (!path) return '-';
                const imageUrl = api.mediaUrl({ path, artifactId: row.artifact_id, datasource });
                if (!imageUrl) return '-';
                return (
                  <a className="uploaded-image-cell" href={imageUrl} target="_blank" rel="noreferrer">
                    <img
                      src={imageUrl}
                      alt={row.original_filename ?? row.image_id ?? 'Imagen'}
                      loading="lazy"
                      decoding="async"
                    />
                    <small>{row.original_filename ?? row.stored_filename ?? row.image_id}</small>
                  </a>
                );
              },
            },
            {
              header: 'Explicación',
              render: (row) => {
                if (!row.explainability_path) return 'No generada';
                const explanationUrl = api.artifactUrl(row.explainability_path, { datasource });
                return (
                  <a className="uploaded-image-cell" href={explanationUrl} target="_blank" rel="noreferrer">
                    <img src={explanationUrl} alt={row.explainability_method ?? 'Explicacion visual'} loading="lazy" decoding="async" />
                    <small>{row.explainability_method ?? 'explicacion visual'}</small>
                  </a>
                );
              },
            },
            { header: 'Modelo', render: (row) => row.model_name ?? '-' },
            {
              header: 'Prediccion', render: (row) => {
                // 1. Validar si existen los datos de la predicción
                // if (!row.predicted_label) return '-';

                // 2. Retornar la lista HTML estructurada con clases CSS o estilos en línea
                return (
                  <ul className="mi-lista">
                    <li className="item-lista">
                      <span className="item-lista-titulo">Prediccion:</span>
                      <span className="item-lista-valor">{row.predicted_label ? row.predicted_label : '-'}</span>
                    </li>
                    <li className="item-lista">
                      <span className="item-lista-titulo">% parasitized:</span>
                      <span className="item-lista-valor">{formatMetric(row.probability_parasitized)}</span>
                    </li>
                    <li className="item-lista">
                      <span className="item-lista-titulo">% uninfected:</span>
                      <span className="item-lista-valor">{formatMetric(row.probability_uninfected)}</span>
                    </li>
                    <li className="item-lista">
                      <span className="item-lista-titulo">Threshold:</span>
                      <span className="item-lista-valor">{formatMetric(row.threshold)}</span>
                    </li>
                    <li className="item-lista">
                      <span className="item-lista-titulo">Confianza:</span>
                      <span className="item-lista-valor">{row.confidence_level ? row.confidence_level : '-'}</span>
                    </li>
                  </ul>
                );
              }
            },
            // { header: 'Prediccion', render: (row) => row.predicted_label ?? '-' },
            // { header: 'Prob. parasitized', render: (row) => formatMetric(probabilityParasitized(row)) },
            // { header: 'Prob. uninfected', render: (row) => formatMetric(row.probability_uninfected) },
            // { header: 'Threshold', render: (row) => formatMetric(row.threshold) },
            // { header: 'Confianza', render: (row) => row.confidence_level ?? '-' },
            { header: 'Calidad', render: (row) => qualityLabel(row) },
            { header: 'Alertas calidad', render: (row) => formatWarnings(row.quality_warnings) },
            { header: 'Calibración', render: (row) => calibrationLabel(row) },
            { header: 'TTA / Ensemble', render: (row) => ttaEnsembleLabel(row) },
            { header: 'Clase real', render: (row) => row.true_label ?? '-' },
            { header: 'Caso', render: (row) => row.case_type ?? '-' },
            { header: 'Decisión', render: (row) => decisionLabel(row) },
            { header: 'Respuesta', render: (row) => row.human_readable_response ?? '-' },

            {
              header: 'Estado', render: (row) => {
                // 1. Validar si existen los datos de la predicción
                // if (!row.predicted_label) return '-';

                // 2. Retornar la lista HTML estructurada con clases CSS o estilos en línea
                return (
                  <ul className="mi-lista">
                    <li>
                      <StatusBadge status={row.run_status ?? 'unknown'} />
                    </li>
                    <li>
                      {formatDate(row.created_at)}
                    </li>
                    <li>
                      <button className="link-button" onClick={() => onRunSelect(row.run_id)} type="button">
                        Ver run
                      </button>
                    </li>
                    {row.explainability_path && onExplainabilityOpen ? (
                      <li>
                        <button className="link-button" onClick={() => onExplainabilityOpen(row.run_id)} type="button">
                          Auditar explicación
                        </button>
                      </li>
                    ) : null}
                  </ul>
                );
              }
            },
            // { header: 'Estado', render: (row) => <StatusBadge status={row.run_status ?? 'unknown'} /> },
            // { header: 'Fecha', render: (row) => formatDate(row.created_at) },
            // {
            //   header: 'Run',
            //   render: (row) => (
            //     <button className="link-button" onClick={() => onRunSelect(row.run_id)} type="button">
            //       Ver run
            //     </button>
            //   ),
            // },
          ]}
        />
      </section>
    </section>
  );
}
