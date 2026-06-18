import { useEffect, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type { ArtifactRow, JsonRecord, RunDetailResponse } from '../types/api';
import { formatDate, formatMetric, stringifyJson } from '../utils/format';

interface RunDetailProps {
  datasource: string;
  runId: string | null;
}

const IMAGE_EXTENSIONS = /\.(png|jpe?g|gif|webp|bmp|svg)$/i;

function isImageArtifact(artifact: ArtifactRow) {
  const mimeType = artifact.mime_type?.toLowerCase() ?? '';
  const artifactType = artifact.artifact_type?.toLowerCase() ?? '';
  const path = artifact.path?.toLowerCase() ?? '';
  const name = artifact.name?.toLowerCase() ?? '';

  return (
    mimeType.startsWith('image/')
    || IMAGE_EXTENSIONS.test(path)
    || IMAGE_EXTENSIONS.test(name)
    || artifactType.includes('image')
    || artifactType === 'confusion_matrix_png'
  );
}

export function RunDetail({ datasource, runId }: RunDetailProps) {
  const [detail, setDetail] = useState<RunDetailResponse | null>(null);
  const [confusion, setConfusion] = useState<JsonRecord[]>([]);
  const [report, setReport] = useState<JsonRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    setError(null);
    Promise.all([
      api.getRun(datasource, runId),
      api.getConfusionMatrix(datasource, runId),
      api.getClassificationReport(datasource, runId),
    ])
      .then(([runResponse, confusionResponse, reportResponse]) => {
        setDetail(runResponse);
        setConfusion(confusionResponse.items);
        setReport(reportResponse.items);
      })
      .catch((err: Error) => setError(err.message));
  }, [datasource, runId]);

  if (!runId) return <section className="panel">Selecciona una ejecucion.</section>;
  if (error) return <section className="panel error">{error}</section>;
  if (!detail) return <Loading />;

  const run = detail.run;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>{String(run.run_name ?? run.id)}</h1>
          <p>{String(run.model_name ?? '-')} / {String(run.dataset_name ?? '-')}</p>
        </div>
        <StatusBadge status={String(run.status ?? 'unknown')} />
      </div>

      <div className="metrics-grid">
        <div className="metric-card"><span>Tipo</span><strong>{String(run.run_type ?? '-')}</strong></div>
        <div className="metric-card"><span>Script</span><strong>{String(run.script_name ?? '-')}</strong></div>
        <div className="metric-card"><span>Inicio</span><strong>{formatDate(String(run.started_at ?? ''))}</strong></div>
        <div className="metric-card"><span>Duracion</span><strong>{formatMetric(run.duration_seconds as number | null)} s</strong></div>
      </div>

      <section className="panel">
        <h2>Parametros</h2>
        <pre>{stringifyJson(run.parameters)}</pre>
      </section>

      <section className="panel">
        <h2>Metricas</h2>
        <DataTable
          rows={detail.metrics}
          columns={[
            { header: 'Nombre', render: (row) => row.metric_name },
            { header: 'Valor', render: (row) => formatMetric(row.metric_value as number | null) },
            { header: 'Split', render: (row) => String(row.split_name ?? '-') },
            { header: 'Clase', render: (row) => String(row.class_name ?? '-') },
          ]}
        />
      </section>

      <div className="grid-two">
        <section className="panel">
          <h2>Matriz de confusion</h2>
          <pre>{stringifyJson(confusion)}</pre>
        </section>
        <section className="panel">
          <h2>Reporte de clasificacion</h2>
          <pre>{stringifyJson(report)}</pre>
        </section>
      </div>

      <section className="panel">
        <h2>Artefactos</h2>
        <div className="artifact-grid">
          {detail.artifacts.map((artifact: ArtifactRow) => {
            const artifactUrl = api.artifactUrl(artifact.path);
            const shouldShowImage = isImageArtifact(artifact);

            return (
              <article key={artifact.id} className="artifact-card">
                <strong>{artifact.name ?? artifact.artifact_type}</strong>
                <small>{artifact.artifact_type}</small>
                {shouldShowImage ? (
                  <a href={artifactUrl} target="_blank" rel="noreferrer">
                    <img src={artifactUrl} alt={artifact.name ?? artifact.artifact_type} />
                  </a>
                ) : null}
                <code>{artifact.path}</code>
                <div className="artifact-actions">
                  <a href={artifactUrl} target="_blank" rel="noreferrer">
                    {shouldShowImage ? 'Abrir imagen' : 'Abrir artefacto'}
                  </a>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </section>
  );
}
