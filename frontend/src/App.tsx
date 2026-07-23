import { useEffect, useState } from 'react';

import { Layout, type PageKey } from './components/Layout';
import { ClinicalEvaluation } from './pages/ClinicalEvaluation';
import { Dashboard } from './pages/Dashboard';
import { DatasetBrowser } from './pages/DatasetBrowser';
import { DatasetsModels } from './pages/DatasetsModels';
import { ErrorsLogs } from './pages/ErrorsLogs';
import { Explainability } from './pages/Explainability';
import { ModelComparison } from './pages/ModelComparison';
import { ModelVersions } from './pages/ModelVersions';
import { Deployments } from './pages/Deployments';
import { Traceability } from './pages/Traceability';
import { RunDetail } from './pages/RunDetail';
import { Runs } from './pages/Runs';
import { UploadedPredictions } from './pages/UploadedPredictions';
import { DEFAULT_DATASOURCE, api } from './services/api';
import type { Datasource, ExplainabilityCase } from './types/api';

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
  const [selectedExplainabilityCase, setSelectedExplainabilityCase] = useState<ExplainabilityCase | null>(null);
  const [selectedExplainabilityRunId, setSelectedExplainabilityRunId] = useState<string | null>(null);
  const [selectedModelVersionId, setSelectedModelVersionId] = useState<string | null>(null);
  const [selectedDeploymentId, setSelectedDeploymentId] = useState<string | null>(null);

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

  const selectModelVersion = (modelVersionId: string) => {
    setSelectedModelVersionId(modelVersionId);
    setSelectedDeploymentId(null);
    setPage('model-versions');
  };

  const selectDeployment = (deploymentId: string) => {
    setSelectedDeploymentId(deploymentId);
    setSelectedModelVersionId(null);
    setPage('deployments');
  };

  const selectExplainabilityCase = (item: ExplainabilityCase) => {
    setSelectedExplainabilityCase(item);
    setSelectedExplainabilityRunId(item.run_id ?? null);
    setPage('explainability');
  };

  const selectRunExplainability = (runId: string) => {
    setSelectedExplainabilityCase(null);
    setSelectedExplainabilityRunId(runId);
    setPage('explainability');
  };

  const selectPage = (nextPage: PageKey) => {
    setSelectedExplainabilityCase(null);
    setSelectedExplainabilityRunId(null);
    if (nextPage !== 'model-versions') setSelectedModelVersionId(null);
    if (nextPage !== 'deployments') setSelectedDeploymentId(null);
    setPage(nextPage);
  };

  const selectDatasource = (nextDatasource: string) => {
    setSelectedExplainabilityCase(null);
    setSelectedExplainabilityRunId(null);
    setSelectedModelVersionId(null);
    setSelectedDeploymentId(null);
    setDatasource(nextDatasource);
  };

  return (
    <Layout
      page={page}
      datasource={datasource}
      datasources={datasources}
      onPageChange={selectPage}
      onDatasourceChange={selectDatasource}
    >
      {page === 'dashboard' ? <Dashboard datasource={datasource} onRunSelect={selectRun} /> : null}
      {page === 'runs' ? (
        <Runs
          datasource={datasource}
          onDeploymentSelect={selectDeployment}
          onModelVersionSelect={selectModelVersion}
          onRunSelect={selectRun}
        />
      ) : null}
      {page === 'clinical-evaluation' ? (
        <ClinicalEvaluation datasource={datasource} onRunSelect={selectRun} />
      ) : null}
      {page === 'models' ? <ModelComparison datasource={datasource} /> : null}
      {page === 'model-versions' ? (
        <ModelVersions
          datasource={datasource}
          onDeploymentSelect={selectDeployment}
          onDeployments={() => selectPage('deployments')}
          onExecutions={() => selectPage('runs')}
          onRunSelect={selectRun}
          selectedModelVersionId={selectedModelVersionId}
        />
      ) : null}
      {page === 'deployments' ? (
        <Deployments
          datasource={datasource}
          onExecutions={() => selectPage('runs')}
          onModelVersionSelect={selectModelVersion}
          selectedDeploymentId={selectedDeploymentId}
        />
      ) : null}
      {page === 'traceability' ? <Traceability datasource={datasource} onRunSelect={selectRun} /> : null}
      {page === 'run-detail' ? (
        <RunDetail
          datasource={datasource}
          runId={selectedRunId}
          onExplainabilitySelect={selectExplainabilityCase}
        />
      ) : null}
      {page === 'explainability' ? (
        <Explainability
          key={datasource}
          datasource={datasource}
          initialCase={selectedExplainabilityCase}
          initialRunId={selectedExplainabilityRunId}
          onRunSelect={selectRun}
        />
      ) : null}
      {page === 'uploaded-predictions' ? (
        <UploadedPredictions
          datasource={datasource}
          onRunSelect={selectRun}
          onExplainabilityOpen={selectRunExplainability}
        />
      ) : null}
      {page === 'dataset-browser' ? <DatasetBrowser datasource={datasource} /> : null}
      {page === 'datasets' ? <DatasetsModels datasource={datasource} /> : null}
      {page === 'errors' ? <ErrorsLogs datasource={datasource} /> : null}
    </Layout>
  );
}

export default App;
