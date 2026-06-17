import { useEffect, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { DomainBadge } from '../components/DomainBadge';
import { Loading } from '../components/Loading';
import { api } from '../services/api';
import type { JsonRecord, ModelSummary } from '../types/api';
import { formatDate, formatMetric, stringifyJson } from '../utils/format';

interface DatasetsModelsProps {
  datasource: string;
}

export function DatasetsModels({ datasource }: DatasetsModelsProps) {
  const [datasets, setDatasets] = useState<JsonRecord[] | null>(null);
  const [models, setModels] = useState<ModelSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    Promise.all([api.getDatasets(datasource), api.getModels(datasource)])
      .then(([datasetResponse, modelResponse]) => {
        setDatasets(datasetResponse.items);
        setModels(modelResponse.items);
      })
      .catch((err: Error) => setError(err.message));
  }, [datasource]);

  if (error) return <section className="panel error">{error}</section>;
  if (!datasets || !models) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Datasets y modelos</h1>
          <p>Catalogo del datasource activo.</p>
        </div>
        <DomainBadge domain={datasource === 'malaria' ? 'Parasitos' : 'Otro'} />
      </div>

      <section className="panel">
        <h2>Datasets</h2>
        <DataTable
          rows={datasets}
          columns={[
            { header: 'Nombre', render: (row) => String(row.name ?? '-') },
            { header: 'Fuente', render: (row) => String(row.source ?? '-') },
            { header: 'Version', render: (row) => String(row.version ?? '-') },
            { header: 'Imagenes', render: (row) => String(row.total_images ?? '-') },
            { header: 'Clases', render: (row) => stringifyJson(row.class_names) },
            { header: 'Creado', render: (row) => formatDate(String(row.created_at ?? '')) },
          ]}
        />
      </section>

      <section className="panel">
        <h2>Modelos</h2>
        <DataTable<ModelSummary>
          rows={models}
          columns={[
            { header: 'Modelo', render: (row) => row.model_name },
            { header: 'Tipo', render: (row) => row.model_type },
            { header: 'Arquitectura', render: (row) => row.architecture ?? '-' },
            { header: 'Runs', render: (row) => row.total_runs },
            { header: 'Accuracy', render: (row) => formatMetric(row.best_accuracy) },
          ]}
        />
      </section>
    </section>
  );
}

