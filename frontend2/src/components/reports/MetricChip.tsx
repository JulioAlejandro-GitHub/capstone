import { formatMetric } from '../../utils/format';

interface MetricChipProps {
  label: string;
  value: number | null | undefined;
}

export function MetricChip({ label, value }: MetricChipProps) {
  return (
    <div className="grid gap-0.5 rounded-lg border border-chip-border bg-chip p-1.75">
      <span className="text-chip-muted text-[10px]">{label}</span>
      <strong className="text-xs text-value tabular-nums">{formatMetric(value)}</strong>
    </div>
  );
}
