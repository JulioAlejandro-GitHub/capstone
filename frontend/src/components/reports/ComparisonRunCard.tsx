import { CopyText } from './ComparisonPython';
import { Link } from 'react-router-dom';
import { useComparisonRun } from '../../hooks/useComparisonRun';
import { routes, withAllowedQuery } from '../../router';
import { getRunDuration } from '../../utils/format';
import { normalizeExecutionParameters, recordValue } from '../../utils/runDetail';
import { StatusPill } from '../ui/StatusPill';

function evidence(...values: unknown[]): string {
  const value = values.find(value => (typeof value === 'string' && value.trim())
    || (typeof value === 'number' && Number.isFinite(value)));
  return value === undefined ? 'Sin evidencia' : String(value);
}

export function ComparisonRunCard({ id, index, datasource, modelName, architecture, onRemove }: {
  id: string; index: number; datasource: string; modelName?: string; architecture?: string | null; onRemove: () => void;
}) {
  const { run, error, retry } = useComparisonRun(datasource, id);
  const parameters = run ? normalizeExecutionParameters(run) : {};
  const cli = recordValue(parameters.cli_arguments) ?? {};
  const snapshot = recordValue(parameters.model_configuration_e2);
  const configuration = recordValue(snapshot?.configuration);
  const resolved = recordValue(configuration?.resolved);
  const optimizer = recordValue(resolved?.optimizer);
  const optimizerParameters = recordValue(optimizer?.parameters);
  const execution = recordValue(resolved?.execution);
  const fields = [
    ['Arquitectura', evidence(run?.architecture, parameters.architecture, cli.architecture, architecture)],
    ['Optimizador', evidence(optimizer?.name, parameters.optimizer, cli.optimizer)],
    ['Learning rate', evidence(optimizerParameters?.learning_rate, parameters.learning_rate, cli.learning_rate)],
    ['Semilla', evidence(run?.random_seed, execution?.seed, parameters.seed, cli.seed)],
    ['Épocas', `${evidence(run?.completed_epochs)} / ${evidence(run?.total_epochs)}`],
  ];
  return <article className="report-section scc-run-card" aria-label={`RUN ${String.fromCharCode(65 + index)}`}>
    <div className="scc-run-bar"><strong>RUN {String.fromCharCode(65 + index)}</strong>
      <button type="button" className="ds-button" data-size="compact" onClick={onRemove} aria-label={`Quitar RUN ${String.fromCharCode(65 + index)}`}>Quitar</button>
    </div>
    <h2><Link className="scc-run-title-link" title="Ir a reporte de TRAIN"
      aria-label={`${evidence(run?.model_name, modelName)}: ir a reporte de TRAIN`}
      to={withAllowedQuery(routes.runDetail(id), { datasource })}>{evidence(run?.model_name, modelName)}</Link></h2>
    {!run && !error && <p role="status">Cargando TRAIN…</p>}
    {error && <div role="alert"><p>{error}</p><button className="ds-button" onClick={retry}>Reintentar</button></div>}
    <dl className="scc-run-facts">{fields.slice(0, 3).map(([label, value]) => <div key={label}><dt title={label === 'Épocas' ? 'Completadas / total' : undefined}>{label}</dt><dd>{value}</dd></div>)}</dl>
    <details><summary>Detalles técnicos</summary><code className="report-identifier">{id}</code><CopyText text={id} label="Copiar UUID" /><dl className="scc-run-facts">{fields.slice(3).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><p>Duración: {run ? getRunDuration(run.started_at, run.finished_at, run.duration_seconds, run.status) : 'Sin evidencia'}</p><p>Evaluación, intento y checkpoint: consultar la selección explícita y el detalle Preflight.</p></details>
    <footer className="scc-run-footer"><StatusPill status={run?.status} label={run?.status ?? 'Sin evidencia'} /></footer>
  </article>;
}
