import { useEffect, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { api } from '../services/api';
import type { JsonRecord } from '../types/api';
import { formatDate } from '../utils/format';

interface ErrorsLogsProps {
  datasource: string;
}

export function ErrorsLogs({ datasource }: ErrorsLogsProps) {
  const [errors, setErrors] = useState<JsonRecord[] | null>(null);
  const [logs, setLogs] = useState<JsonRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    Promise.all([api.getErrors(datasource), api.getLogs(datasource)])
      .then(([errorResponse, logResponse]) => {
        setErrors(errorResponse.items);
        setLogs(logResponse.items);
      })
      .catch((err: Error) => setError(err.message));
  }, [datasource]);

  if (error) return <section className="panel error">{error}</section>;
  if (!errors || !logs) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Errores y logs</h1>
          <p>Observabilidad registrada por los scripts de ejecucion.</p>
        </div>
      </div>

      <section className="panel">
        <h2>Errores</h2>
        <DataTable
          rows={errors}
          columns={[
            { header: 'Fecha', render: (row) => formatDate(String(row.created_at ?? '')) },
            { header: 'Run', render: (row) => String(row.run_name ?? row.run_id ?? '-') },
            { header: 'Modelo', render: (row) => String(row.model_name ?? '-') },
            { header: 'Tipo', render: (row) => String(row.error_type ?? '-') },
            { header: 'Mensaje', render: (row) => String(row.error_message ?? '-') },
          ]}
        />
      </section>

      <section className="panel">
        <h2>Logs</h2>
        <DataTable
          rows={logs}
          columns={[
            { header: 'Fecha', render: (row) => formatDate(String(row.created_at ?? '')) },
            { header: 'Nivel', render: (row) => String(row.log_level ?? '-') },
            { header: 'Run', render: (row) => String(row.run_name ?? row.run_id ?? '-') },
            { header: 'Fuente', render: (row) => String(row.source ?? '-') },
            { header: 'Mensaje', render: (row) => String(row.message ?? '-') },
          ]}
        />
      </section>
    </section>
  );
}

