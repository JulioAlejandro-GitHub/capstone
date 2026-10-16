import { useEffect, useMemo, useState } from 'react';
import { api } from '../../services/api';
import type { AssessmentChoice, AssessmentDetail } from '../../types/api';
import { GeneratedXAIComparison } from './GeneratedXAIComparison';
import type { XAIComparison } from './xai/comparison';

export function AssessmentSampleXAI({detail, datasource}: {detail: AssessmentDetail; datasource: string}) {
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
    {sample ? <GeneratedXAIComparison key={comparison.id} comparison={comparison} datasource={datasource} /> : <p>El contexto no registra muestras.</p>}
  </section>;
}

export function TrainingAssessmentXAI({trainingRunId, datasource}: {trainingRunId: string; datasource: string}) {
  const [choices, setChoices] = useState<AssessmentChoice[]>([]);
  const [selected, setSelected] = useState('');
  const [detail, setDetail] = useState<AssessmentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setChoices([]); setSelected(''); setDetail(null); setError(null); setLoading(true);
    const load = async () => {
      const all: AssessmentChoice[] = [];
      for (let offset = 0; !controller.signal.aborted; offset += 100) {
        const page = await api.getTrainingAssessments(trainingRunId, offset, controller.signal);
        if (page.items.some(item => item.training_run_id !== trainingRunId)) throw new Error('Linaje TRAIN incompatible.');
        all.push(...page.items.filter(item => item.split === 'val' && item.purpose === 'development'));
        if (page.items.length < 100) break;
      }
      if (!controller.signal.aborted) { setChoices(all); setSelected(all[0]?.attempt_id ?? ''); setLoading(false); }
    };
    void load().catch((failure: unknown) => { if (!controller.signal.aborted) { setError(String(failure)); setLoading(false); } });
    return () => controller.abort();
  }, [trainingRunId]);
  useEffect(() => {
    setDetail(null);
    if (!selected) return;
    const controller = new AbortController();
    void api.getExplainContext(selected, controller.signal).then(value => {
      if (controller.signal.aborted) return;
      if (value.id !== selected || value.training_run_id !== trainingRunId) throw new Error('Contexto incompatible.');
      setDetail(value);
    }).catch((failure: unknown) => { if (!controller.signal.aborted) setError(String(failure)); });
    return () => controller.abort();
  }, [selected, trainingRunId]);
  return <details className="ds-report ds-accordion"><summary>Generar explicabilidad por célula</summary>
    {error && <p role="alert">{error}</p>}
    {loading && <p role="status">Cargando contextos científicos…</p>}
    {!loading && !choices.length && <p>Se requiere un contexto EVALUATE o EXPLAIN de VAL registrado para seleccionar una célula.</p>}
    {choices.length > 0 && <label>Contexto científico<select className="ds-control" value={selected} onChange={event => setSelected(event.target.value)}>
      {choices.map(choice => <option key={choice.attempt_id} value={choice.attempt_id}>{choice.kind} · {choice.attempt_id}</option>)}
    </select></label>}
    {detail && <AssessmentSampleXAI key={detail.id} detail={detail} datasource={datasource} />}
  </details>;
}
