import { useCallback, useEffect, useId, useMemo, useState } from 'react';

import { Loading } from '../components/Loading';
import { ApiError, api } from '../services/api';
import type { DatasetVersionSummary } from '../types/api';
import type {
  CampaignCatalog,
  CampaignConfiguration as CampaignConfigurationDocument,
  CampaignModel,
  CampaignParameter,
  CampaignPreview,
  ParameterValue,
  SavedCampaign,
} from '../types/campaign';

// SWV2.2: one page to configure, validate and save a campaign. Models, parameters, domains,
// defaults and the Total de Experimentos come from the backend; this page never starts TRAIN.

interface CampaignConfigurationProps { datasource: string }

const number = new Intl.NumberFormat('es-CL');
const PREVIEW_DELAY_MS = 350;
const SECTION_LABELS: Record<CampaignParameter['section'], string> = {
  architecture: 'Arquitectura',
  fine_tuning: 'Fine-tuning',
  training: 'Entrenamiento',
  selection: 'Selección y robustez',
};
const ERROR_MESSAGES: Record<string, string> = {
  REQUIRED_NON_EMPTY_LIST: 'Selecciona al menos un valor.',
  INVALID_ITEM: 'Contiene valores inválidos.',
  DUPLICATE_ITEM: 'Contiene valores duplicados.',
  INVALID_PARAMETER_VALUE: 'Valor fuera del dominio permitido.',
  PARAMETER_NOT_EDITABLE: 'Este parámetro es fijo para la arquitectura.',
  INVALID_VARIANT_NAME: 'Nombre de variante inválido.',
  DUPLICATE_VARIANT_NAME: 'Nombre de variante duplicado.',
  DATASET_VERSION_REQUIRED: 'Selecciona una dataset version.',
  DATASET_VERSION_NOT_FOUND: 'La dataset version no existe.',
  DATASET_VERSION_NOT_TRAINABLE: 'La dataset version no está disponible para entrenamiento.',
  EQUIVALENT_VARIANTS_DUPLICATE_MEMBER: 'Dos variantes producen la misma configuración para un modelo.',
  INCOMPATIBLE_FINE_TUNING: 'El fine-tuning requiere capas descongeladas mayores que 0.',
  TOTAL_UNAVAILABLE: 'El total se calcula cuando la configuración es válida.',
};

function message(code: string) {
  const base = code.split(':')[0];
  return ERROR_MESSAGES[base] ?? `Configuración rechazada por el contrato (${code}).`;
}

function errorCode(error: unknown) {
  if (error instanceof ApiError) {
    try {
      const body = JSON.parse(error.message) as { error?: { details?: { code?: string } } };
      return body.error?.details?.code ?? error.code ?? error.message;
    } catch {
      return error.code ?? error.message;
    }
  }
  return error instanceof Error ? error.message : 'Error desconocido.';
}

function newCampaignId() {
  return crypto.randomUUID();
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function editableDefaults(model: CampaignModel) {
  return Object.fromEntries(model.parameters.filter((p) => p.editable).map((p) => [p.key, p.default]));
}

function formatCommand(command: string) {
  return command.replace(/ --/g, ' \\\n  --');
}

function parseSeeds(text: string): number[] | null {
  const tokens = text.split(/[\s,;]+/).filter(Boolean);
  if (!tokens.length || tokens.some((t) => !/^\d+$/.test(t))) return null;
  return tokens.map(Number);
}

function ParameterControl({ parameter, value, error, onChange }: {
  parameter: CampaignParameter; value: ParameterValue; error?: string; onChange: (value: ParameterValue) => void;
}) {
  const inputId = useId();
  if (!parameter.editable) {
    return <div className="campaign-field is-fixed">
      <span className="campaign-field-label">{parameter.label}</span>
      <span className="campaign-fixed-value">{String(parameter.default)}</span>
      {parameter.note ? <small>{parameter.note}</small> : null}
    </div>;
  }
  let control;
  if (parameter.type === 'boolean') {
    control = <label className="campaign-switch">
      <input id={inputId} type="checkbox" checked={value === true} onChange={(e) => onChange(e.target.checked)} />
      <span>{value === true ? 'Sí' : 'No'}</span>
    </label>;
  } else if (parameter.type === 'enum') {
    control = <select id={inputId} value={String(value)} onChange={(e) => onChange(e.target.value)}>
      {(parameter.choices ?? []).map((choice) => <option key={choice} value={choice}>{choice}</option>)}
    </select>;
  } else {
    control = <input
      id={inputId}
      type="number"
      inputMode={parameter.type === 'integer' ? 'numeric' : 'decimal'}
      step={parameter.type === 'integer' ? 1 : 'any'}
      min={parameter.minimum}
      max={parameter.maximum}
      value={typeof value === 'number' ? value : String(value)}
      onChange={(e) => {
        // Invalid text is sent as-is so the backend reports it; never silently coerced.
        const raw = e.target.value.trim();
        const valid = parameter.type === 'integer' ? /^-?\d+$/.test(raw) : raw !== '' && Number.isFinite(Number(raw));
        onChange(valid ? Number(raw) : e.target.value);
      }}
    />;
  }
  return <div className={`campaign-field ${error ? 'has-error' : ''}`}>
    <label className="campaign-field-label" htmlFor={inputId}>{parameter.label}</label>
    {control}
    <small>
      Default: {String(parameter.default)}
      {parameter.minimum !== undefined ? ` · mín ${parameter.minimum}` : ''}
      {parameter.maximum !== undefined ? ` · ${parameter.exclusive_maximum ? '<' : 'máx'} ${parameter.maximum}` : ''}
    </small>
    {error ? <small className="campaign-error" role="alert">{message(error)}</small> : null}
  </div>;
}

function ModelConfiguration({ model, values, fieldErrors, prefix, onChange }: {
  model: CampaignModel; values: Record<string, ParameterValue>; fieldErrors: Record<string, string>;
  prefix: string; onChange: (key: string, value: ParameterValue) => void;
}) {
  const sections = (Object.keys(SECTION_LABELS) as CampaignParameter['section'][])
    .map((section) => [section, model.parameters.filter((p) => p.section === section)] as const)
    .filter(([, items]) => items.length);
  const hasError = Object.keys(fieldErrors).some((field) => field.startsWith(`${prefix}.`));
  return <details className={`campaign-model-config ${hasError ? 'has-error' : ''}`} open>
    <summary>
      <strong>{model.label}</strong>
      <small>{model.id} · adapter {model.adapter_version} · {model.strategies.join(' + ')}</small>
    </summary>
    {sections.map(([section, items]) => <fieldset key={section} className="campaign-parameter-group">
      <legend>{SECTION_LABELS[section]}</legend>
      <div className="campaign-parameter-grid">
        {items.map((parameter) => <ParameterControl
          key={parameter.key}
          parameter={parameter}
          value={values[parameter.key] ?? parameter.default}
          error={fieldErrors[`${prefix}.${parameter.key}`]}
          onChange={(value) => onChange(parameter.key, value)}
        />)}
      </div>
    </fieldset>)}
  </details>;
}

function SavedCampaignPanel({ saved, reloaded, onReset }: {
  saved: SavedCampaign; reloaded: SavedCampaign | null; onReset: () => void;
}) {
  const [copied, setCopied] = useState('');
  const command = formatCommand(saved.command);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied('Comando copiado');
    } catch {
      setCopied('No fue posible copiar; selecciona el texto manualmente.');
    }
  };
  const consistent = reloaded !== null && reloaded.campaign_id === saved.campaign_id
    && reloaded.total_experiments === saved.total_experiments
    && reloaded.dataset_version_id === saved.dataset_version_id
    && reloaded.contract_hash === saved.contract_hash;
  return <section className="panel campaign-saved" aria-live="polite">
    <h2>Campaña guardada</h2>
    <dl className="campaign-saved-grid">
      <div><dt>Campaign ID</dt><dd><code>{saved.campaign_id}</code></dd></div>
      <div><dt>Dataset Version</dt><dd><code>{saved.dataset_version_id}</code></dd></div>
      <div><dt>Total de Experimentos</dt><dd><strong>{number.format(saved.total_experiments)}</strong></dd></div>
      <div><dt>Configuraciones</dt><dd>{number.format(saved.configurations.length)}</dd></div>
      <div><dt>Estado</dt><dd>{saved.state}</dd></div>
      <div><dt>Contract hash</dt><dd><code title={saved.contract_hash}>{saved.contract_hash.slice(0, 16)}…</code></dd></div>
    </dl>
    <p className="campaign-reload">
      {reloaded === null ? 'Verificando la campaña recargada desde PostgreSQL v2…'
        : consistent ? '✓ Recargada desde PostgreSQL v2 por campaign_id: mismo dataset, mismo contrato y mismo Total de Experimentos.'
          : '✗ La campaña recargada no coincide con la guardada.'}
    </p>
    <h3>Comando de ejecución</h3>
    <pre className="campaign-command"><code>{command}</code></pre>
    <div className="campaign-actions">
      <button type="button" className="campaign-secondary" onClick={copy}>Copiar</button>
      <small role="status">{copied}</small>
    </div>
    <p className="api-note">Ejecuta este comando manualmente desde la consola para iniciar la campaña.</p>
    <button type="button" className="campaign-secondary" onClick={onReset}>Configurar otra campaña</button>
  </section>;
}

export function CampaignConfiguration({ datasource }: CampaignConfigurationProps) {
  const [catalog, setCatalog] = useState<CampaignCatalog | null>(null);
  const [datasets, setDatasets] = useState<DatasetVersionSummary[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [purpose, setPurpose] = useState('');
  const [datasetVersionId, setDatasetVersionId] = useState<string>('');
  const [presetId, setPresetId] = useState('');
  const [configuration, setConfiguration] = useState<CampaignConfigurationDocument | null>(null);
  const [seedText, setSeedText] = useState('');
  const [preview, setPreview] = useState<CampaignPreview | null>(null);
  const [previewKey, setPreviewKey] = useState('');
  const [previewing, setPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [campaignId, setCampaignId] = useState(newCampaignId);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState<SavedCampaign | null>(null);
  const [reloaded, setReloaded] = useState<SavedCampaign | null>(null);

  const applyPreset = useCallback((source: CampaignCatalog, id: string) => {
    const preset = source.presets.find((item) => item.id === id) ?? source.presets[0];
    setPresetId(preset.id);
    setConfiguration(clone(preset.configuration));
    setSeedText(preset.configuration.seeds.join(', '));
  }, []);

  const load = useCallback(() => {
    setLoadError(null);
    Promise.all([api.getCampaignCatalog(), api.getDatasetVersions(datasource)])
      .then(([nextCatalog, versions]) => {
        setCatalog(nextCatalog);
        setDatasets(versions.items);
        applyPreset(nextCatalog, nextCatalog.default_preset);
        // Preselect only when exactly one version is trainable; otherwise the operator chooses.
        const trainable = versions.items.filter((item) => item.status === 'FROZEN' && item.trainable);
        setDatasetVersionId((current) => current || (trainable.length === 1 ? trainable[0].dataset_version_id : ''));
      })
      .catch((error) => setLoadError(errorCode(error)));
  }, [applyPreset, datasource]);

  useEffect(load, [load]);

  const models = useMemo(() => new Map((catalog?.models ?? []).map((m) => [m.id, m])), [catalog]);
  const selectedDataset = datasets.find((item) => item.dataset_version_id === datasetVersionId) ?? null;
  const seeds = parseSeeds(seedText);
  const requestKey = configuration && seeds ? JSON.stringify({ configuration: { ...configuration, seeds }, datasetVersionId }) : '';

  useEffect(() => {
    if (!configuration || !seeds || saved) return undefined;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setPreviewing(true);
      setPreviewError(null);
      api.previewCampaign({ ...configuration, seeds }, datasetVersionId || null, controller.signal)
        .then((result) => { setPreview(result); setPreviewKey(requestKey); })
        .catch((error) => { if (!controller.signal.aborted) setPreviewError(errorCode(error)); })
        .finally(() => { if (!controller.signal.aborted) setPreviewing(false); });
    }, PREVIEW_DELAY_MS);
    return () => { controller.abort(); window.clearTimeout(timer); };
    // requestKey captures configuration, seeds and dataset.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestKey, saved]);

  const fieldErrors = useMemo(() => Object.fromEntries(
    (previewKey === requestKey ? preview?.errors ?? [] : []).map((e) => [e.field, e.code])), [preview, previewKey, requestKey]);

  const update = (change: (draft: CampaignConfigurationDocument) => void) => {
    setConfiguration((current) => {
      if (!current) return current;
      const draft = clone(current);
      change(draft);
      return draft;
    });
  };

  const toggleModel = (id: string, on: boolean) => update((draft) => {
    const model = models.get(id);
    if (!model) return;
    draft.models = on ? [...draft.models, id] : draft.models.filter((m) => m !== id);
    draft.variants.forEach((variant) => {
      if (on) variant.parameters[id] = variant.parameters[id] ?? editableDefaults(model);
      else delete variant.parameters[id];
    });
  });

  const toggleOptimizer = (id: string, on: boolean) => update((draft) => {
    draft.optimizers = on ? [...draft.optimizers, id] : draft.optimizers.filter((o) => o !== id);
  });

  const addVariant = () => update((draft) => {
    const names = new Set(draft.variants.map((v) => v.name));
    let index = draft.variants.length + 1;
    while (names.has(`configuracion_${index}`)) index += 1;
    draft.variants.push({
      name: `configuracion_${index}`,
      parameters: Object.fromEntries(draft.models.map((id) => [id, editableDefaults(models.get(id)!)])),
    });
  });

  const reset = () => {
    setSaved(null);
    setReloaded(null);
    setSaveError(null);
    setName('');
    setPurpose('');
    setCampaignId(newCampaignId());
    if (catalog) applyPreset(catalog, catalog.default_preset);
  };

  const currentPreview = previewKey === requestKey ? preview : null;
  const generalReady = name.trim().length > 0 && purpose.trim().length > 0;
  const canSave = Boolean(currentPreview?.valid && generalReady && !previewing && !saving && seeds && configuration);

  const save = async () => {
    if (!configuration || !seeds || !canSave) return;
    setSaving(true);
    setSaveError(null);
    try {
      const result = await api.createCampaign({
        campaign_id: campaignId, name: name.trim(), purpose: purpose.trim(), dataset_version_id: datasetVersionId,
        configuration: { ...configuration, seeds },
      });
      setSaved(result);
      api.getCampaign(result.campaign_id).then(setReloaded).catch((error) => setSaveError(errorCode(error)));
    } catch (error) {
      setSaveError(errorCode(error));
    } finally {
      setSaving(false);
    }
  };

  if (loadError) {
    return <section className="page"><div className="panel warning-panel">
      <h1>Campaña</h1>
      <p>No fue posible cargar el catálogo de campañas ({loadError}).</p>
      <button type="button" onClick={load}>Reintentar</button>
    </div></section>;
  }
  if (!catalog || !configuration) return <Loading />;

  if (saved) {
    return <section className="page campaign-page">
      <div className="page-title"><div><h1>Campaña</h1><p>Configuración guardada en PostgreSQL v2.</p></div></div>
      <SavedCampaignPanel saved={saved} reloaded={reloaded} onReset={reset} />
      {saveError ? <p className="campaign-error" role="alert">{message(saveError)}</p> : null}
    </section>;
  }

  const supportedOptimizers = catalog.optimizers.filter((o) =>
    configuration.models.every((id) => models.get(id)?.optimizers.includes(o.id)));
  const summary = currentPreview?.summary ?? null;
  const fixed = catalog.protocol.fixed;

  return <section className="page campaign-page">
    <div className="page-title">
      <div>
        <h1>Configurar campaña</h1>
        <p>Define dataset, modelos y parámetros; al guardar obtienes el comando para ejecutarla desde consola.</p>
      </div>
    </div>

    <div className="campaign-layout">
      <div className="campaign-form">
        <section className="panel">
          <h2>1. Datos generales</h2>
          <div className="campaign-parameter-grid">
            <div className={`campaign-field ${name.trim() ? '' : 'is-pending'}`}>
              <label className="campaign-field-label" htmlFor="campaign-name">Nombre</label>
              <input id="campaign-name" value={name} maxLength={200} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className={`campaign-field campaign-field-wide ${purpose.trim() ? '' : 'is-pending'}`}>
              <label className="campaign-field-label" htmlFor="campaign-purpose">Propósito / descripción</label>
              <textarea id="campaign-purpose" rows={2} value={purpose} maxLength={2000}
                onChange={(e) => setPurpose(e.target.value)} />
            </div>
          </div>
        </section>

        <section className="panel">
          <h2>2. Dataset Version</h2>
          <div className="campaign-field">
            <label className="campaign-field-label" htmlFor="campaign-dataset">dataset-version-id</label>
            <select id="campaign-dataset" value={datasetVersionId} onChange={(e) => setDatasetVersionId(e.target.value)}>
              <option value="">Selecciona una dataset version…</option>
              {datasets.map((item) => <option key={item.dataset_version_id} value={item.dataset_version_id}
                disabled={!(item.status === 'FROZEN' && item.trainable)}>
                {item.dataset_version_id} · {item.name} v{item.semantic_version} · {item.status}
                {item.trainable ? '' : ' (no disponible para entrenamiento)'}
              </option>)}
            </select>
            {fieldErrors.dataset_version_id ? <small className="campaign-error">{message(fieldErrors.dataset_version_id)}</small> : null}
          </div>
          {selectedDataset ? <dl className="campaign-dataset-grid">
            <div><dt>UUID</dt><dd><code>{selectedDataset.dataset_version_id}</code></dd></div>
            <div><dt>Estado</dt><dd>{selectedDataset.status}{selectedDataset.trainable ? ' · disponible para entrenamiento' : ''}</dd></div>
            <div><dt>TRAIN</dt><dd>{number.format(selectedDataset.train_records)}</dd></div>
            <div><dt>VALIDATION</dt><dd>{number.format(selectedDataset.val_records)}</dd></div>
            <div><dt>TEST</dt><dd>{number.format(selectedDataset.test_records)}</dd></div>
            <div><dt>Total</dt><dd>{number.format(selectedDataset.source_record_count)}</dd></div>
            <div><dt>Pacientes</dt><dd>{number.format(selectedDataset.patient_count)}</dd></div>
            <div><dt>Versión</dt><dd>{selectedDataset.name} v{selectedDataset.semantic_version}</dd></div>
          </dl> : <p className="api-note">La campaña consume una dataset version existente; no crea ni modifica splits.</p>}
        </section>

        <section className="panel">
          <h2>3. Modelos</h2>
          <div className="campaign-field">
            <label className="campaign-field-label" htmlFor="campaign-preset">Valores iniciales</label>
            <select id="campaign-preset" value={presetId} onChange={(e) => applyPreset(catalog, e.target.value)}>
              {catalog.presets.map((preset) => <option key={preset.id} value={preset.id}>{preset.label}</option>)}
            </select>
            <small>Cambiar los valores iniciales reemplaza modelos, optimizadores, semillas, variantes y EarlyStopping.</small>
          </div>
          <div className="campaign-checklist" role="group" aria-label="Modelos">
            {catalog.models.map((model) => <label key={model.id} className="campaign-check">
              <input type="checkbox" checked={configuration.models.includes(model.id)}
                onChange={(e) => toggleModel(model.id, e.target.checked)} />
              <span><strong>{model.label}</strong><small>{model.id} · adapter {model.adapter_version}</small></span>
            </label>)}
          </div>
          {fieldErrors.models ? <small className="campaign-error">{message(fieldErrors.models)}</small> : null}

          <h3>Optimizadores</h3>
          <div className="campaign-checklist" role="group" aria-label="Optimizadores">
            {catalog.optimizers.map((optimizer) => {
              const supported = supportedOptimizers.some((o) => o.id === optimizer.id);
              return <label key={optimizer.id} className={`campaign-check ${supported ? '' : 'is-disabled'}`}>
                <input type="checkbox" disabled={!supported && !configuration.optimizers.includes(optimizer.id)}
                  checked={configuration.optimizers.includes(optimizer.id)}
                  onChange={(e) => toggleOptimizer(optimizer.id, e.target.checked)} />
                <span><strong>{optimizer.label}</strong>
                  <small>LR base {optimizer.learning_rate} · LR fine-tuning {optimizer.fine_tune_learning_rate}</small></span>
              </label>;
            })}
          </div>
          {fieldErrors.optimizers ? <small className="campaign-error">{message(fieldErrors.optimizers)}</small> : null}
          <p className="api-note">Los hiperparámetros internos de cada optimizador provienen de sus defaults versionados
            (perfil batch) y no son editables en esta fase.</p>

          <h3>Semillas</h3>
          <div className={`campaign-field ${seeds ? '' : 'has-error'}`}>
            <label className="campaign-field-label" htmlFor="campaign-seeds">Semillas compartidas por todos los modelos</label>
            <input id="campaign-seeds" value={seedText} onChange={(e) => setSeedText(e.target.value)} />
            <small>Enteros entre {catalog.seeds.minimum} y {catalog.seeds.maximum}, separados por coma. Cada semilla
              es un experimento por configuración.</small>
            {!seeds ? <small className="campaign-error" role="alert">Ingresa enteros no negativos separados por coma.</small>
              : fieldErrors.seeds ? <small className="campaign-error">{message(fieldErrors.seeds)}</small> : null}
          </div>
        </section>

        <section className="panel">
          <h2>4. Configuración de modelos</h2>
          {configuration.variants.map((variant, index) => <article key={index} className="campaign-variant">
            <header>
              <div className="campaign-field">
                <label className="campaign-field-label" htmlFor={`variant-${index}`}>Variante de configuración</label>
                <input id={`variant-${index}`} value={variant.name}
                  onChange={(e) => update((draft) => { draft.variants[index].name = e.target.value; })} />
                {fieldErrors[`variants[${index}].name`] ? <small className="campaign-error">
                  {message(fieldErrors[`variants[${index}].name`])}</small> : null}
              </div>
              {configuration.variants.length > 1 ? <button type="button" className="campaign-secondary"
                onClick={() => update((draft) => { draft.variants.splice(index, 1); })}>Quitar variante</button> : null}
            </header>
            {configuration.models.map((id) => {
              const model = models.get(id);
              return model ? <ModelConfiguration
                key={id}
                model={model}
                values={variant.parameters[id] ?? {}}
                fieldErrors={fieldErrors}
                prefix={`variants[${index}].parameters.${id}`}
                onChange={(key, value) => update((draft) => {
                  draft.variants[index].parameters[id] = { ...draft.variants[index].parameters[id], [key]: value };
                })}
              /> : null;
            })}
          </article>)}
          <button type="button" className="campaign-secondary" onClick={addVariant}>Agregar variante de configuración</button>

          <h3>EarlyStopping y presupuesto (comunes a la campaña)</h3>
          <div className="campaign-parameter-grid">
            {catalog.protocol.editable.map((item) => {
              const [section, leaf] = item.key.split('.') as ['early_stopping' | 'budget', string];
              const value = (configuration.protocol[section] as Record<string, ParameterValue>)[leaf];
              return <ParameterControl
                key={item.key}
                parameter={{ ...item, section: 'training', path: item.key, editable: true, source: catalog.protocol.source }}
                value={value}
                error={fieldErrors[`protocol.${item.key}`]}
                onChange={(next) => update((draft) => {
                  (draft.protocol[section] as Record<string, ParameterValue>)[leaf] = next;
                })}
              />;
            })}
          </div>
          <dl className="campaign-fixed-grid">
            <div><dt>Monitor EarlyStopping</dt><dd>{String(fixed['early_stopping.monitor'])} ({String(fixed['early_stopping.mode'])})</dd></div>
            <div><dt>Checkpoint</dt><dd>{String(fixed['checkpoint.policy'])} · {String(fixed['checkpoint.monitor'])} ({String(fixed['checkpoint.mode'])})</dd></div>
            <div><dt>Umbral de selección</dt><dd>{String(fixed['checkpoint.threshold'])}</dd></div>
            <div><dt>Objetivo de sensibilidad</dt><dd>{String(fixed.sensitivity_target)}</dd></div>
            <div><dt>Especificidad mínima</dt><dd>{String(fixed.specificity_minimum)}</dd></div>
            <div><dt>Calibración</dt><dd>{String(fixed['calibration.algorithm'])}</dd></div>
            <div><dt>Acceso a TEST</dt><dd>{String(fixed.test_access)}</dd></div>
          </dl>
          <small className="campaign-source">Protocolo base: {catalog.protocol.template_version} ({catalog.protocol.source}).
            Los valores fijos pertenecen al protocolo científico aprobado.</small>
        </section>
      </div>

      <aside className="campaign-aside">
        <section className="panel campaign-summary">
          <h2>5. Resumen de campaña</h2>
          <dl>
            <div><dt>Dataset Version</dt><dd>{datasetVersionId ? <code title={datasetVersionId}>{datasetVersionId.slice(0, 8)}…</code> : '—'}</dd></div>
            <div><dt>Modelos seleccionados</dt><dd>{configuration.models.length}</dd></div>
            <div><dt>Optimizadores</dt><dd>{configuration.optimizers.length}</dd></div>
            <div><dt>Semillas</dt><dd>{seeds ? seeds.length : '—'}</dd></div>
            <div><dt>Variantes</dt><dd>{configuration.variants.length}</dd></div>
            <div><dt>Configuraciones</dt><dd>{summary ? number.format(summary.configurations) : '—'}</dd></div>
            <div className="campaign-total"><dt>Total de Experimentos</dt>
              <dd>{previewing ? 'Calculando…' : summary ? number.format(summary.total_experiments) : '—'}</dd></div>
          </dl>
          {summary ? <ul className="campaign-per-model">
            {Object.entries(summary.experiments_per_model).map(([id, count]) =>
              <li key={id}>{models.get(id)?.label ?? id}: {number.format(count)}</li>)}
          </ul> : null}
          <small>{catalog.experiment_formula}. Calculado por el backend con la misma lógica que construye la campaña.</small>
        </section>

        <section className="panel campaign-validation">
          <h2>6. Validación</h2>
          <ul>
            <li className={generalReady ? 'is-pass' : 'is-fail'}>{generalReady ? '✓' : '✗'} Datos generales</li>
            {(currentPreview?.checks ?? []).map((check) => <li key={check.check}
              className={check.status === 'PASS' ? 'is-pass' : 'is-fail'}>
              {check.status === 'PASS' ? '✓' : '✗'} {check.label}
              {check.status === 'FAIL' && check.errors.length ? <small>{message(check.errors[0].code)}</small> : null}
            </li>)}
          </ul>
          {!currentPreview && !previewError ? <small>Validando con el backend…</small> : null}
          {previewError ? <small className="campaign-error" role="alert">No fue posible validar ({previewError}).</small> : null}
          {saveError ? <p className="campaign-error" role="alert">{message(saveError)}</p> : null}
          <button type="button" className="campaign-primary" disabled={!canSave} onClick={save}>
            {saving ? 'Guardando…' : 'Guardar campaña'}
          </button>
        </section>
      </aside>
    </div>
  </section>;
}
