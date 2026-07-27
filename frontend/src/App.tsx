import { useEffect, useMemo, useState } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { Layout } from './components/Layout';
import { ProtectedRoute } from './auth';
import { InvalidEntityId, NotFound, RouteEffects } from './components/RouteState';
import { ClinicalEvaluation } from './pages/ClinicalEvaluation';
import { Dashboard } from './pages/Dashboard';
import { DatasetBrowser } from './pages/DatasetBrowser';
import { DatasetsModels } from './pages/DatasetsModels';
import { Deployments } from './pages/Deployments';
import { ErrorsLogs } from './pages/ErrorsLogs';
import { Explainability } from './pages/Explainability';
import { ModelComparison } from './pages/ModelComparison';
import { ModelVersions } from './pages/ModelVersions';
import { RunDetail } from './pages/RunDetail';
import { Stage2ReleaseDetail } from './pages/Stage2ReleaseDetail';
import { Runs } from './pages/Runs';
import { Traceability } from './pages/Traceability';
import { UploadedPredictions } from './pages/UploadedPredictions';
import { Login } from './pages/Login';
import { SmearUpload } from './pages/SmearUpload';
import { isValidPublicId, routes, withAllowedQuery } from './router';
import { DEFAULT_DATASOURCE, api } from './services/api';
import type { Datasource } from './types/api';

const fallbackDatasource: Datasource = {
  key: 'malaria', label: 'Malaria', domain: 'Parasitos', enabled: true, database: 'malaria_experiments',
};

function LegacyRunRedirect() {
  const { legacyId } = useParams();
  const normalized = legacyId?.replace(/^RunId=/i, '');
  const [search] = useSearchParams();
  return isValidPublicId(normalized)
    ? <Navigate replace to={`${routes.runDetail(normalized)}?${search.toString()}`} />
    : <InvalidEntityId kind="ejecución" listPath={routes.runs} />;
}

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [datasources, setDatasources] = useState<Datasource[]>([fallbackDatasource]);
  const requestedDatasource = searchParams.get('datasource');
  const datasource = useMemo(() => {
    const allowed = datasources.find((item) => item.enabled && item.key === requestedDatasource);
    return allowed?.key ?? datasources.find((item) => item.enabled)?.key ?? DEFAULT_DATASOURCE;
  }, [datasources, requestedDatasource]);

  useEffect(() => {
    api.getDatasources().then((response) => setDatasources(response.items)).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (requestedDatasource === datasource) return;
    const next = new URLSearchParams(searchParams);
    next.set('datasource', datasource);
    setSearchParams(next, { replace: true });
  }, [datasource, requestedDatasource, searchParams, setSearchParams]);

  const go = (pathname: string, extra: Record<string, string | null | undefined> = {}) =>
    navigate(withAllowedQuery(pathname, { datasource, ...extra }));
  const selectDatasource = (next: string) => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('datasource', next);
    setSearchParams(nextParams);
  };
  const common = { datasource };

  return <>
    <RouteEffects />
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute><Layout datasource={datasource} datasources={datasources} onDatasourceChange={selectDatasource} /></ProtectedRoute>}>
        <Route path="/" element={<Navigate replace to={withAllowedQuery(routes.summary, { datasource })} />} />
        <Route path={routes.summary} element={<Dashboard {...common} onRunSelect={(id) => go(routes.runDetail(id))} />} />
        <Route path={routes.runs} element={<Runs {...common} onRunSelect={(id) => go(routes.runDetail(id))} />} />
        <Route path={`${routes.runs}/:trainingRunId`} element={<RunDetailRoute datasource={datasource} go={go} />} />
        <Route path={`${routes.runs}/:trainingRunId/liberacion`} element={<Stage2ReleaseDetail datasource={datasource} />} />
        <Route path={`${routes.runs}/RunId=:legacyId`} element={<LegacyRunRedirect />} />
        <Route path={routes.evaluations} element={<ClinicalEvaluation {...common} onRunSelect={(id) => go(routes.runDetail(id))} />} />
        <Route path={routes.comparison} element={<ModelComparison {...common} />} />
        <Route path={routes.modelVersions} element={<ModelVersionsRoute datasource={datasource} go={go} />} />
        <Route path={`${routes.modelVersions}/:modelVersionId`} element={<ModelVersionsRoute datasource={datasource} go={go} />} />
        <Route path={routes.deployments} element={<DeploymentsRoute datasource={datasource} go={go} />} />
        <Route path={`${routes.deployments}/:deploymentId`} element={<DeploymentsRoute datasource={datasource} go={go} />} />
        <Route path={routes.traceability} element={<Traceability {...common} onRunSelect={(id) => go(routes.runDetail(id))} />} />
        <Route path={routes.explainability} element={<Explainability {...common} onRunSelect={(id) => go(routes.runDetail(id))} />} />
        <Route path={routes.predictions} element={<UploadedPredictions {...common} onRunSelect={(id) => go(routes.runDetail(id))}
          onExplainabilityOpen={() => go(routes.explainability)} />} />
        <Route path={routes.dataset} element={<DatasetBrowser {...common} />} />
        <Route path={routes.datasetsModels} element={<DatasetsModels {...common} />} />
        <Route path={routes.errorsLogs} element={<ErrorsLogs {...common} />} />
        <Route path={routes.smearUpload} element={<SmearUpload />} />
        <Route path="/runs" element={<Navigate replace to={`${routes.runs}${location.search}`} />} />
        <Route path="/evaluations" element={<Navigate replace to={`${routes.evaluations}${location.search}`} />} />
        <Route path="/model-versions" element={<Navigate replace to={`${routes.modelVersions}${location.search}`} />} />
        <Route path="/deployments" element={<Navigate replace to={`${routes.deployments}${location.search}`} />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  </>;
}

function RunDetailRoute({ datasource, go }: { datasource: string; go: (path: string) => void }) {
  const { trainingRunId } = useParams();
  if (!isValidPublicId(trainingRunId)) return <InvalidEntityId kind="ejecución" listPath={withAllowedQuery(routes.runs, { datasource })} />;
  return <RunDetail datasource={datasource} runId={trainingRunId} onExplainabilitySelect={() => go(routes.explainability)} />;
}

function ModelVersionsRoute({ datasource, go }: { datasource: string; go: (path: string) => void }) {
  const { modelVersionId } = useParams();
  if (modelVersionId && !isValidPublicId(modelVersionId)) return <InvalidEntityId kind="modelo liberado" listPath={withAllowedQuery(routes.modelVersions, { datasource })} />;
  return <ModelVersions datasource={datasource} selectedModelVersionId={modelVersionId ?? null}
    onRunSelect={(id) => go(routes.runDetail(id))} onModelVersionSelect={(id) => go(id ? routes.modelVersionDetail(id) : routes.modelVersions)}
    onDeploymentSelect={(id) => go(routes.deploymentDetail(id))}
    onDeployments={() => go(routes.deployments)} onExecutions={() => go(routes.runs)} />;
}

function DeploymentsRoute({ datasource, go }: { datasource: string; go: (path: string) => void }) {
  const { deploymentId } = useParams();
  if (deploymentId && !isValidPublicId(deploymentId)) return <InvalidEntityId kind="deployment" listPath={withAllowedQuery(routes.deployments, { datasource })} />;
  return <Deployments datasource={datasource} selectedDeploymentId={deploymentId ?? null}
    onExecutions={() => go(routes.runs)} onModelVersionSelect={(id) => go(routes.modelVersionDetail(id))}
    onAnalysis={() => go(routes.predictions)} onDeploymentSelect={(id) => go(id ? routes.deploymentDetail(id) : routes.deployments)} />;
}

export default App;
