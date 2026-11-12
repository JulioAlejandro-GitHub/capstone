interface StatusBadgeProps {
  status?: string | null;
}

/* Traducción de .status / .status-completed / .status-failed / .status-started */
const STATUS_TONE: Record<string, string> = {
  completed: 'bg-ok-soft text-ok',
  failed: 'bg-danger-soft text-danger',
  started: 'bg-warn-soft text-warn',
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status ?? 'unknown';
  return (
    <span className={`inline-flex items-center rounded-pill px-2.5 py-1.25 text-xs font-bold ${STATUS_TONE[normalized] ?? 'bg-neutral-soft text-neutral-fg'}`}>
      {normalized}
    </span>
  );
}
