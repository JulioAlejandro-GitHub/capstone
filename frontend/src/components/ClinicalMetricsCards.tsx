import type { ClinicalMetrics } from '../types/api';
import { formatMetric } from '../utils/format';

interface ClinicalMetricsCardsProps {
  metrics: ClinicalMetrics | null | undefined;
  minRecall?: number | null;
}

const metricItems: Array<{
  key: keyof ClinicalMetrics;
  label: string;
  hint: string;
}> = [
  {
    key: 'recall_parasitized',
    label: 'Recall parasitized',
    hint: 'Capacidad de detectar células parasitadas.',
  },
  {
    key: 'specificity',
    label: 'Specificity',
    hint: 'Capacidad de descartar células no parasitadas.',
  },
  {
    key: 'f2_parasitized',
    label: 'F2-score',
    hint: 'Da mayor peso al recall y a los falsos negativos.',
  },
  {
    key: 'pr_auc_parasitized',
    label: 'PR-AUC',
    hint: 'Área bajo precision-recall para parasitized.',
  },
  {
    key: 'roc_auc_parasitized',
    label: 'ROC-AUC',
    hint: 'Separación global entre ambas clases.',
  },
  {
    key: 'accuracy',
    label: 'Accuracy',
    hint: 'Proporción total de clasificaciones correctas.',
  },
];

const TECHNICAL_REFERENCE = 0.8;

function metricState(
  key: keyof ClinicalMetrics,
  value: number | null | undefined,
  minRecall: number | null | undefined,
) {
  if (value === null || value === undefined) {
    return { label: 'Sin datos', kind: 'unknown' };
  }
  if (key === 'recall_parasitized' && minRecall !== null && minRecall !== undefined) {
    return value >= minRecall
      ? { label: 'Cumple referencia', kind: 'ok' }
      : { label: 'Bajo referencia', kind: 'warning' };
  }
  if (['recall_parasitized', 'specificity', 'f2_parasitized', 'pr_auc_parasitized'].includes(key)) {
    return value < TECHNICAL_REFERENCE
      ? { label: 'Revisar', kind: 'warning' }
      : null;
  }
  return null;
}

export function ClinicalMetricsCards({ metrics, minRecall }: ClinicalMetricsCardsProps) {
  return (
    <div className="metrics-grid clinical-metrics-grid">
      {metricItems.map((item) => {
        const value = metrics?.[item.key] as number | null | undefined;
        const state = metricState(item.key, value, minRecall);
        return (
          <div
            className={`metric-card clinical-metric-card${state ? ` clinical-metric-card--${state.kind}` : ''}`}
            key={String(item.key)}
            title={item.hint}
          >
            <div className="clinical-metric-card__heading">
              <span>{item.label}</span>
              {state ? <small className="clinical-metric-card__state">{state.label}</small> : null}
            </div>
            <strong>{formatMetric(value)}</strong>
            <small>{item.hint}</small>
          </div>
        );
      })}
    </div>
  );
}
