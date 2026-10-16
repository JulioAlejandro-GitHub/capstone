import { useMemo, useRef, useState } from 'react';
import { api } from '../../services/api';
import type { AssessmentChoice, AssessmentDetail } from '../../types/api';
import { GeneratedXAIComparison } from './GeneratedXAIComparison';
import { createComparisonCache } from '../../utils/comparisonCache';
import { useComparisonEvidence } from '../../hooks/useComparisonEvidence';
import type { XAIComparison } from './xai/comparison';

export function AssessmentSampleXAI({detail, datasource, active, onEvidenceChange}: {detail: AssessmentDetail; datasource: string; active?: boolean; onEvidenceChange?: () => void}) {
  const samples = detail.identity.samples ?? [];
  const [selection, setSelection] = useState('');
  const sample = samples.some(row => row.sample_id === selection) ? selection : samples[0]?.sample_id;
  const comparison = useMemo<XAIComparison>(() => ({
    id: `${detail.id}:${sample}`, trainingRunId: detail.training_run_id,
    datasetVersionId: detail.identity.dataset?.dataset_version_id,
    checkpointArtifactId: detail.identity.model.checkpoint_artifact_id,
    modelVersionId: detail.identity.model.model_version_id,
    targetClass: detail.identity.explanation?.class ?? 1,
    split: detail.identity.split, purpose: detail.identity.purpose, sampleId: sample,
    methods: {}, original: sample && detail.identity.dataset ? {
      method: 'original', execution: 'completed', availability: 'available', attemptId: detail.id,
      assessmentIdentityId: detail.identity_id,
      originalSource: {source: 'dataset_sample', trainingRunId: detail.training_run_id,
        datasetVersionId: detail.identity.dataset.dataset_version_id, sampleId: sample, attemptId: detail.id},
    } : undefined,
  }), [detail, sample]);
  if (detail.identity.split !== 'val' || detail.identity.purpose !== 'development') {
    return <p>La generación por caso requiere el contexto autorizado VAL / development.</p>;
  }
  return <section className="ds-report">
    <label>Célula del contexto seleccionado<select className="ds-control" value={sample ?? ''} onChange={event => setSelection(event.target.value)}>
      {samples.map(row => <option key={row.sample_id} value={row.sample_id}>{row.sample_id}</option>)}
    </select></label>
    {sample ? <GeneratedXAIComparison key={comparison.id} comparison={comparison} datasource={datasource} active={active} onEvidenceChange={onEvidenceChange} /> : <p>El contexto no registra muestras.</p>}
  </section>;
}

export function TrainingAssessmentXAI(props: {trainingRunId: string; datasource: string; active?: boolean; onEvidenceChange?: () => void}) {
  const [visited, setVisited] = useState(false);
  const [open, setOpen] = useState(false);
  return <details className="ds-report ds-accordion" onToggle={event => { setOpen(event.currentTarget.open); if (event.currentTarget.open) setVisited(true); }}>
    <summary>Generar explicabilidad por célula</summary>
    {visited && <TrainingAssessmentXAIContent key={`${props.datasource}:${props.trainingRunId}`} {...props} active={open && props.active !== false} />}
  </details>;
}

function TrainingAssessmentXAIContent({trainingRunId, datasource, active, onEvidenceChange}: {trainingRunId: string; datasource: string; active: boolean; onEvidenceChange?: () => void}) {
  const cache = useMemo(createComparisonCache, []);
  const visible = useRef(active);
  visible.current = active;
  const [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState('');
  const choices = useComparisonEvidence(cache, JSON.stringify(['xai-contexts', datasource, trainingRunId, revision]), async () => {
    const all: AssessmentChoice[] = [];
    for (let offset = 0; ; offset += 100) {
      if (!visible.current) throw new Error('Consulta pausada al cerrar XAI.');
      const page = await api.getTrainingAssessments(trainingRunId, offset);
      if (page.items.some(item => item.training_run_id !== trainingRunId)) throw new Error('Linaje TRAIN incompatible.');
      all.push(...page.items.filter(item => item.split === 'val' && item.purpose === 'development'));
      if (page.items.length < 100) return all;
    }
  }, active);
  const detail = useComparisonEvidence(cache, selected ? JSON.stringify(['xai-context', datasource, trainingRunId, selected, revision]) : null, async () => {
    const value = await api.getExplainContext(selected);
    if (value.id !== selected || value.training_run_id !== trainingRunId) throw new Error('Contexto incompatible.');
    return value;
  }, active);
  const refresh = () => { cache.clear(); setRevision(value => value + 1); };
  return <section>
    {(choices.error || detail.error) ? <div role="alert"><p>No se pudo consultar el contexto XAI.</p><button className="ds-button" onClick={refresh}>Reintentar XAI</button></div> : null}
    {(choices.loading || detail.loading) && <p role="status">Cargando contextos científicos…</p>}
    {choices.data && !choices.data.length && <p>Se requiere un contexto EVALUATE o EXPLAIN de VAL registrado para seleccionar una célula.</p>}
    {choices.data && choices.data.length > 0 && <label>Contexto científico<select className="ds-control" value={selected} onChange={event => setSelected(event.target.value)}>
      <option value="">Selecciona un intento explícitamente</option>
      {choices.data.map(choice => <option key={choice.attempt_id} value={choice.attempt_id}>{choice.kind} · {choice.attempt_id}</option>)}
    </select></label>}
    <button className="ds-button" onClick={refresh}>Actualizar evidencia XAI</button>
    {detail.data && <AssessmentSampleXAI key={`${detail.data.id}:${revision}`} detail={detail.data} datasource={datasource} active={active} onEvidenceChange={onEvidenceChange} />}
  </section>;
}
