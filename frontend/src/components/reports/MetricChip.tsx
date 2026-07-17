import { formatMetric } from '../../utils/format';

interface MetricChipProps {
  label: string;
  value: number | null | undefined;
}

export function MetricChip({ label, value }: MetricChipProps) {
  return (
    <div className="metric-chip">
      <span>{label}</span>
      <strong>{formatMetric(value)}</strong>
    </div>
  );
}
