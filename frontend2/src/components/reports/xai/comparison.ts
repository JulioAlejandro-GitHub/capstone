import type { AssessmentArtifact, AssessmentDetail, JsonValue } from '../../../types/api';

export const XAI_METHODS = ['gradcam', 'lime', 'shap'] as const;
export type XAIMethod = typeof XAI_METHODS[number];
export type XAIExecution = 'not_executed' | 'pending' | 'running' | 'completed' | 'failed';
export type XAIAvailability = 'available' | 'no_evidence' | 'missing' | 'denied' | 'integrity_failed' | 'not_comparable' | 'error';
export interface XAIArtifact {
  artifactId: string;
  source: 'assessment' | 'training';
  attemptId?: string;
  trainingRunId?: string;
  sha256?: string;
  bytes?: number;
}
export interface XAIDatasetSample {
  source: 'dataset_sample';
  trainingRunId: string;
  datasetVersionId: string;
  sampleId: string;
  attemptId: string;
}
export interface XAIEvidence {
  method: XAIMethod | 'original';
  execution: XAIExecution;
  availability: XAIAvailability;
  artifact?: XAIArtifact;
  // Raw attribution (NumPy float32, model input resolution) behind the overlay image.
  mapArtifact?: XAIArtifact;
  originalSource?: XAIDatasetSample;
  attemptId?: string;
  assessmentIdentityId?: string;
  message?: string;
  metadata?: JsonValue;
  referenceSampleIds?: string[];
}
export interface XAIComparison {
  id: string;
  trainingRunId: string;
  modelVersionId?: string;
  checkpointArtifactId?: string;
  sampleId?: string;
  datasetVersionId?: string;
  split?: string;
  purpose?: string;
  prediction?: string;
  trueClass?: string;
  targetClass?: 0 | 1;
  // Governed record of the explained cell, read once from any identity that lists it.
  sampleRecord?: { relativePath?: string; label?: number };
  // The model's decision on this cell, from the EVALUATE of the same split (label, predicted class, raw score).
  outcome?: { label: number; predicted: number; score: number; threshold: number; split: string; attemptId: string };
  comparabilityIssue?: string;
  original?: XAIEvidence;
  methods: Partial<Record<XAIMethod, XAIEvidence>>;
}
export interface XAIAttemptPage { detail: AssessmentDetail; artifacts: AssessmentArtifact[] }
export const XAI_LABELS = { original: 'Célula original', gradcam: 'Grad-CAM', lime: 'LIME', shap: 'SHAP' };

function execution(state: string): XAIExecution {
  if (state === 'verified') return 'completed';
  if (state === 'active') return 'running';
  if (state === 'failed' || state === 'interrupted') return 'failed';
  return 'pending';
}

function canonicalContext(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalContext).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.entries(value).sort(([a], [b]) => a.localeCompare(b))
    .map(([key, entry]) => `${JSON.stringify(key)}:${canonicalContext(entry)}`).join(',')}}`;
  return JSON.stringify(value) ?? 'null';
}

/** Only explicit identities establish equivalence. No filenames, ordering or SHAP background. */
export function groupXAIComparisons(pages: XAIAttemptPage[], trainingRunId: string): XAIComparison[] {
  const groups = new Map<string, XAIComparison>();
  const seen = new Set<string>();
  for (const {detail, artifacts} of pages) {
    if (detail.kind !== 'explain' || detail.training_run_id !== trainingRunId) continue;
    const method = detail.identity.explanation?.method;
    if (!XAI_METHODS.includes(method as XAIMethod)) continue;
    const model = detail.identity.model;
    // Empty attempts remain visible but cannot be assigned to an invented sample.
    const overlays: (AssessmentArtifact | undefined)[] = artifacts.filter(a => a.role === 'overlay');
    if (!overlays.length) overlays.push(undefined);
    for (const artifact of overlays) {
      const duplicateKey = JSON.stringify([detail.id, artifact?.artifact_id]);
      if (seen.has(duplicateKey)) continue;
      seen.add(duplicateKey);
      const relationMismatch = artifact && (artifact.attempt_id !== detail.id || artifact.training_run_id !== trainingRunId);
      const sampleId = artifact?.sample_id || undefined;
      const map = sampleId ? artifacts.find(item => item.role === 'map' && item.sample_id === sampleId && item.attempt_id === detail.id) : undefined;
      const datasetVersionId = detail.identity.dataset?.dataset_version_id;
      const complete = sampleId && model.model_version_id && model.checkpoint_artifact_id && datasetVersionId && detail.identity.split && detail.identity.purpose;
      const issue = relationMismatch ? 'La referencia no acredita pertenencia al intento y TRAIN.'
        : !complete ? 'Identidad de muestra, modelo, checkpoint o contexto de datos incompleta; evidencia aislada.' : undefined;
      // Preserve additional producer context (preprocessing, decision policy, etc.).
      // Method-specific parameters/background are deliberately not equivalence keys.
      const operationalKeys = new Set(['explanation', 'samples', 'campaign_id', 'execution_id', 'seed', 'batch_size', 'code', 'kind', 'schema', 'evaluation', 'metrics_definition', 'http_request']);
      const context: Record<string, unknown> = Object.fromEntries(Object.entries(detail.identity).filter(([key]) => !operationalKeys.has(key)));
      // Storage locations are not scientific identities (Mac and Docker differ).
      context.model = Object.fromEntries(Object.entries(model).filter(([key]) => key !== 'path' && key !== 'source'));
      context.dataset = Object.fromEntries(Object.entries(detail.identity.dataset ?? {}).filter(([key]) => key !== 'dataset_root'));
      const targetClass = detail.identity.explanation?.class;
      const identityKey = JSON.stringify([targetClass, canonicalContext(context), trainingRunId, model.model_version_id, model.checkpoint_artifact_id, sampleId, datasetVersionId, detail.identity.split, detail.identity.purpose]);
      let key = issue ? JSON.stringify([identityKey, detail.id, artifact?.artifact_id]) : identityKey;
      // Repeated evidence for one method is preserved as another row, never overwritten.
      if (groups.get(key)?.methods[method as XAIMethod]) key = JSON.stringify([key, detail.id, artifact?.artifact_id]);
      const row: XAIComparison = groups.get(key) ?? { id: key, trainingRunId, modelVersionId: model.model_version_id,
        checkpointArtifactId: model.checkpoint_artifact_id, sampleId, datasetVersionId,
        split: detail.identity.split, purpose: detail.identity.purpose, targetClass, comparabilityIssue: issue, methods: {} };
      if (!row.original && !relationMismatch && sampleId && datasetVersionId) {
        row.original = {
          method: 'original', execution: 'completed', availability: 'available',
          attemptId: detail.id, assessmentIdentityId: detail.identity_id,
          originalSource: {source: 'dataset_sample', trainingRunId, datasetVersionId, sampleId, attemptId: detail.id},
          metadata: {provenance: 'dataset_split_assignments.source_record_id', datasetVersionId, sampleId, split: detail.identity.split},
        };
      }
      const listed = (detail.identity.samples as {sample_id: string; relative_path?: string; label?: number}[] | undefined)?.find(item => item.sample_id === sampleId);
      if (listed && !row.sampleRecord?.relativePath) row.sampleRecord = {relativePath: listed.relative_path, label: listed.label};
      const methods: XAIComparison['methods'] = row.methods;
      methods[method as XAIMethod] = {
        method: method as XAIMethod, execution: execution(detail.state),
        availability: relationMismatch ? 'not_comparable' : artifact ? 'available' : 'no_evidence',
        attemptId: detail.id, assessmentIdentityId: detail.identity_id,
        message: relationMismatch ? issue : detail.cause ?? (!artifact ? 'No hay overlay registrado en esta página del intento.' : undefined),
        artifact: artifact && !relationMismatch ? { artifactId: artifact.artifact_id, source: 'assessment',
          attemptId: detail.id, trainingRunId, sha256: artifact.sha256, bytes: artifact.bytes } : undefined,
        mapArtifact: map && !relationMismatch ? { artifactId: map.artifact_id, source: 'assessment',
          attemptId: detail.id, trainingRunId, sha256: map.sha256, bytes: map.bytes } : undefined,
        referenceSampleIds: method === 'shap' ? detail.identity.explanation?.background?.map(sample => sample.sample_id) : undefined,
        metadata: { identity: detail.identity, verification: detail.verification, state: detail.state } as JsonValue,
      };
      groups.set(key, row);
    }
  }
  return [...groups.values()];
}
