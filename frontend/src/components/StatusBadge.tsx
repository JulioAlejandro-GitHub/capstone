interface StatusBadgeProps {
  status?: string | null;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status ?? 'unknown';
  return <span className={`status status-${normalized}`}>{normalized}</span>;
}

