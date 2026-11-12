interface MetricCardProps {
  label: string;
  value: string | number | null | undefined;
  hint?: string;
}

export function MetricCard({ label, value, hint }: MetricCardProps) {
  return (
    <div className="grid gap-1.5 rounded-panel border border-border bg-surface p-4.5 shadow-panel">
      <span className="text-muted">{label}</span>
      <strong className="text-metric text-value">{value ?? '-'}</strong>
      {hint ? <small className="text-muted">{hint}</small> : null}
    </div>
  );
}
