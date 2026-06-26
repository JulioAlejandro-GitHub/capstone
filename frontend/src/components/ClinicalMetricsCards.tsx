import type { ClinicalMetrics } from '../types/api';
import { formatMetric } from '../utils/format';

interface ClinicalMetricsCardsProps {
  metrics: ClinicalMetrics | null | undefined;
}

const metricItems: Array<{
  key: keyof ClinicalMetrics;
  label: string;
  hint: string;
}> = [
  {
    key: 'recall_parasitized',
    label: 'Sensitivity / Recall parasitized',
    hint: 'Proporcion de celulas parasitadas correctamente detectadas.',
  },
  {
    key: 'specificity',
    label: 'Specificity',
    hint: 'Proporcion de celulas no infectadas correctamente descartadas.',
  },
  {
    key: 'f2_parasitized',
    label: 'F2-score',
    hint: 'Da mayor peso al recall; util cuando falsos negativos son mas criticos.',
  },
  {
    key: 'pr_auc_parasitized',
    label: 'PR-AUC',
    hint: 'Area bajo precision-recall para la clase parasitized.',
  },
  {
    key: 'roc_auc_parasitized',
    label: 'ROC-AUC',
    hint: 'Separacion global usando probability_parasitized.',
  },
  {
    key: 'balanced_accuracy',
    label: 'Balanced accuracy',
    hint: 'Promedio balanceado entre sensibilidad y especificidad.',
  },
  {
    key: 'precision_parasitized',
    label: 'Precision parasitized',
    hint: 'Proporcion de predicciones parasitized que eran parasitized.',
  },
  {
    key: 'accuracy',
    label: 'Accuracy',
    hint: 'Proporcion total de clasificaciones correctas.',
  },
];

export function ClinicalMetricsCards({ metrics }: ClinicalMetricsCardsProps) {
  return (
    <div className="metrics-grid clinical-metrics-grid">
      {metricItems.map((item) => (
        <div className="metric-card" key={String(item.key)}>
          <span>{item.label}</span>
          <strong>{formatMetric(metrics?.[item.key] as number | null | undefined)}</strong>
          <small>{item.hint}</small>
        </div>
      ))}
    </div>
  );
}
