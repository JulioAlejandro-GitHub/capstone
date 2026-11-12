interface DomainBadgeProps {
  domain?: string | null;
}

export function DomainBadge({ domain }: DomainBadgeProps) {
  return (
    <span className="inline-flex items-center rounded-pill bg-accent-soft px-2.5 py-1.25 text-xs font-bold text-accent">
      {domain ?? 'Otro'}
    </span>
  );
}
