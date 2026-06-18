import { useEffect, useState } from 'react';

import { Layout, type PageKey } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { DatasetsModels } from './pages/DatasetsModels';
import { ErrorsLogs } from './pages/ErrorsLogs';
import { Explainability } from './pages/Explainability';
import { ModelComparison } from './pages/ModelComparison';
import { RunDetail } from './pages/RunDetail';
import { Runs } from './pages/Runs';
import { UploadedPredictions } from './pages/UploadedPredictions';
import { DEFAULT_DATASOURCE, api } from './services/api';
import type { Datasource } from './types/api';

function App() {
  const [page, setPage] = useState<PageKey>('dashboard');
  const [datasource, setDatasource] = useState(DEFAULT_DATASOURCE);
  const [datasources, setDatasources] = useState<Datasource[]>([
    {
      key: 'malaria',
      label: 'Malaria',
      domain: 'Parasitos',
      enabled: true,
      database: 'malaria_experiments',
    },
  ]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDatasources()
      .then((response) => setDatasources(response.items))
      .catch(() => undefined);
  }, []);

  const selectRun = (runId: string) => {
    setSelectedRunId(runId);
    setPage('run-detail');
  };

  return (
    <Layout
      page={page}
      datasource={datasource}
      datasources={datasources}
      onPageChange={setPage}
      onDatasourceChange={setDatasource}
    >
      {page === 'dashboard' ? <Dashboard datasource={datasource} onRunSelect={selectRun} /> : null}
      {page === 'runs' ? <Runs datasource={datasource} onRunSelect={selectRun} /> : null}
      {page === 'models' ? <ModelComparison datasource={datasource} /> : null}
      {page === 'run-detail' ? <RunDetail datasource={datasource} runId={selectedRunId} /> : null}
      {page === 'explainability' ? <Explainability datasource={datasource} /> : null}
      {page === 'uploaded-predictions' ? (
        <UploadedPredictions datasource={datasource} onRunSelect={selectRun} />
      ) : null}
      {page === 'datasets' ? <DatasetsModels datasource={datasource} /> : null}
      {page === 'errors' ? <ErrorsLogs datasource={datasource} /> : null}
    </Layout>
  );
}

export default App;
