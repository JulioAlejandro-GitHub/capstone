import { useEffect, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type { PagedResponse, UploadedPrediction } from '../types/api';
import { formatDate, formatMetric } from '../utils/format';


interface UploadedPredictionsProps {
  datasource: string;
  onRunSelect: (runId: string) => void;
}


function uploadedImagePath(row: UploadedPrediction) {
  return row.artifact_path ?? row.image_path;
}

function probabilityParasitized(row: UploadedPrediction) {
  return row.probability_parasitized ?? row.score_positive_label;
}


export function UploadedPredictions({ datasource, onRunSelect }: UploadedPredictionsProps) {
  const [predictions, setPredictions] = useState<PagedResponse<UploadedPrediction> | null>(null);
  const [modelName, setModelName] = useState('');
  const [predictedLabel, setPredictedLabel] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    setPredictions(null);
    api
      .getUploadedPredictions(datasource, {
        model_name: modelName || undefined,
        predicted_label: predictedLabel || undefined,
        limit: 100,
      })
      .then(setPredictions)
      .catch((err: Error) => setError(err.message));
  }, [datasource, modelName, predictedLabel]);

  if (error) return <section className="panel error">{error}</section>;
  if (!predictions) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Predicciones subidas</h1>
          <p>Imagenes externas evaluadas con src.predict_image y registradas con --track-db.</p>
        </div>
      </div>

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
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Consultas registradas</h2>
          <span>{predictions.total} registros</span>
        </div>
        <DataTable<UploadedPrediction>
          rows={predictions.items}
          emptyText="No hay imagenes subidas para prediccion registradas en BD."
          columns={[
            {
              header: 'Imagen',
              render: (row) => {
                const path = uploadedImagePath(row);
                if (!path) return '-';
                return (
                  <div className="uploaded-image-cell">
                    <img src={api.artifactUrl(path)} alt={row.original_filename ?? row.image_id ?? 'Imagen'} />
                    <small>{row.original_filename ?? row.stored_filename ?? row.image_id}</small>
                  </div>
                );
              },
            },
            { header: 'Modelo', render: (row) => row.model_name ?? '-' },
            { header: 'Prediccion', render: (row) => row.predicted_label ?? '-' },
            { header: 'Prob. parasitized', render: (row) => formatMetric(probabilityParasitized(row)) },
            { header: 'Prob. uninfected', render: (row) => formatMetric(row.probability_uninfected) },
            { header: 'Threshold', render: (row) => formatMetric(row.threshold) },
            { header: 'Confianza', render: (row) => row.confidence_level ?? '-' },
            { header: 'Clase real', render: (row) => row.true_label ?? '-' },
            { header: 'Caso', render: (row) => row.case_type ?? '-' },
            { header: 'Estado', render: (row) => <StatusBadge status={row.run_status ?? 'unknown'} /> },
            { header: 'Fecha', render: (row) => formatDate(row.created_at) },
            {
              header: 'Run',
              render: (row) => (
                <button className="link-button" onClick={() => onRunSelect(row.run_id)} type="button">
                  Ver run
                </button>
              ),
            },
          ]}
        />
      </section>
    </section>
  );
}
