import { useState } from 'react';
import type { PreflightResponse, JsonValue } from '../../types/scientificPreflight';

export const configurationLabels: Record<string, string> = {
  architecture: 'Arquitectura', random_seed: 'Semilla', optimizer: 'Optimizador', learning_rate: 'Learning rate',
  batch_size: 'Tamaño de lote', loss_function: 'Función de pérdida', max_epochs: 'Épocas máximas',
  normalization: 'Normalización', internal_preprocessing: 'Preprocesamiento interno', no_augment: 'Sin aumento de datos',
  checkpoint_monitor: 'Monitor de checkpoint', checkpoint_mode: 'Modo de checkpoint', early_stopping: 'Parada temprana',
  fine_tune_epochs: 'Épocas de ajuste fino', fine_tune_learning_rate: 'Learning rate de ajuste fino',
  early_stopping_patience: 'Paciencia', early_stopping_monitor: 'Monitor de parada', early_stopping_mode: 'Modo de parada',
  restore_best_weights: 'Restaurar mejores pesos', dropout: 'Dropout', l2: 'Regularización L2',
  input_height: 'Alto de entrada', input_width: 'Ancho de entrada', input_channels: 'Canales de entrada',
};
export function configurationEvidence(data: PreflightResponse, selectionId: string) {
  return data.evidence.filter(ref => ref.source === 'A4' && ref.selection_ids.includes(selectionId));
}
export function pythonLiteral(value: JsonValue): string {
  if (value === null) return 'None';
  if (typeof value === 'boolean') return value ? 'True' : 'False';
  if (Array.isArray(value)) return `[${value.map(pythonLiteral).join(', ')}]`;
  if (typeof value === 'object') return `{${Object.entries(value).map(([key, item]) => `${JSON.stringify(key)}: ${pythonLiteral(item)}`).join(', ')}}`;
  return JSON.stringify(value);
}
export function configurationCode(data: PreflightResponse, selectionId: string): string {
  const blocks = configurationEvidence(data, selectionId).flatMap((ref, index) => {
    if (ref.value.state !== 'known' || !ref.value.value || typeof ref.value.value !== 'object' || Array.isArray(ref.value.value)) return [];
    const entries = Object.entries(ref.value.value).filter(([key, value]) => key in configurationLabels && value !== null && typeof value !== 'object');
    return entries.length ? [`config_${index + 1} = {\n${entries.map(([key, value]) => `    ${JSON.stringify(key)}: ${pythonLiteral(value)},`).join('\n')}\n}`] : [];
  });
  // Separate records preserve conflicting evidence rather than silently overwriting values.
  return '# Configuración persistida · proyección pública A4\n# No acredita por sí sola la ejecución efectiva ni reconstruye capas.\n' + (blocks.join('\n\n') || '# Sin parámetros acreditados disponibles.');
}

export function CopyText({ text, label }: { text: string; label: string }) {
  const [status, setStatus] = useState('');
  return <span className="scc-copy"><button type="button" className="ds-button" data-size="compact" onClick={async () => {
    try { await navigator.clipboard.writeText(text); setStatus('Copiado'); } catch { setStatus('No se pudo copiar. Selecciona el texto para copiarlo.'); }
  }}>{label}</button><span role="status">{status}</span></span>;
}
export function ComparisonPython({ data }: { data: PreflightResponse }) {
  const [selected, setSelected] = useState(data.selections[0]?.selection_id ?? '');
  const [view, setView] = useState('configuration');
  const selection = data.selections.find(item => item.selection_id === selected) ?? data.selections[0];
  if (!selection) return <p>Selecciona un TRAIN.</p>;
  const code = view === 'configuration' ? configurationCode(data, selection.selection_id) : '# Reconstrucción no acreditada\n# Nivel 1: consulta los parámetros persistidos en Configuración.\n# Nivel 2: falta constructor versionado o estructura serializada acreditada.\n# Nivel 3: falta verificación de integridad y compatibilidad del checkpoint.\n# Un registro de checkpoint no acredita sus bytes.\n# No se genera ni ejecuta un modelo.';
  const refs = configurationEvidence(data, selection.selection_id);
  const descriptors = refs.flatMap(ref => {
    const value = ref.value.state === 'known' ? ref.value.value : null;
    return value && typeof value === 'object' && !Array.isArray(value)
      ? [typeof value.architecture === 'string' ? value.architecture : 'Arquitectura sin evidencia', typeof value.optimizer === 'string' ? value.optimizer : 'Optimizador sin evidencia'] : [];
  });
  return <details className="ds-accordion scc-python"><summary>Ver modelo en Python</summary>
    <div className="scc-python-controls"><label>TRAIN<select className="ds-control" value={selection.selection_id} onChange={event => setSelected(event.target.value)}>{data.selections.map((item, index) => <option key={item.selection_id} value={item.selection_id}>RUN {String.fromCharCode(65 + index)}</option>)}</select></label>
      <label>Vista<select className="ds-control" value={view} onChange={event => setView(event.target.value)}><option value="configuration">Configuración</option><option value="reconstruction">Reconstrucción</option></select></label><CopyText key={code} text={code} label="Copiar código" /></div>
    <p>{descriptors.join(' · ') || 'Arquitectura y optimizador sin evidencia'}</p>
    <p>Procedencia: evidencia pública persistida A4. Los parámetros ausentes se omiten; no se completan con valores predeterminados.</p>
    <pre tabIndex={0} aria-label="Código Python"><code>{code.split(/(#[^\n]*|"(?:\\.|[^"\\])*"|\b(?:True|False|None)\b|\b\d+(?:\.\d+)?(?:e[+-]?\d+)?\b)/g).map((part, index) => <span key={index} className={part.startsWith('#') ? 'scc-code-comment' : part.startsWith('"') ? 'scc-code-string' : /^(True|False|None|\d)/.test(part) ? 'scc-code-value' : undefined}>{part}</span>)}</code></pre>
    <details><summary>Procedencia y evidencia faltante</summary><code className="report-identifier">{selection.training_run_id}</code>{refs.map(ref => <p key={ref.evidence_id}>{ref.operation} · {ref.evidence_id} · {ref.observed_at} · {ref.verification}{ref.value.state !== 'known' && 'reason' in ref.value ? ` · ${ref.value.reason}` : ''}</p>)}<p>{refs.length ? 'Los campos ausentes o nulos no se incluyen en el código.' : 'Sin evidencia A4 para este TRAIN.'}</p><p>Este contrato no separa configuración declarada de ejecución efectiva ni acredita la arquitectura serializada.</p></details>
  </details>;
}
