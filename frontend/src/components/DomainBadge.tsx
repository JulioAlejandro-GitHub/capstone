interface DomainBadgeProps {
  domain?: string | null;
}

export function DomainBadge({ domain }: DomainBadgeProps) {
  return <span className="domain-badge">{domain ?? 'Otro'}</span>;
}

