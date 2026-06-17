interface MetricCardProps {
  label: string;
  value: string | number | null | undefined;
  hint?: string;
}

export function MetricCard({ label, value, hint }: MetricCardProps) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value ?? '-'}</strong>
      {hint ? <small>{hint}</small> : null}
    </div>
  );
}

