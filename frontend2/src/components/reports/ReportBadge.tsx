import type { ReactNode } from 'react';

import type { RunAnalysisLevel } from '../../utils/runReport';

export type ReportBadgeLevel = RunAnalysisLevel | 'info';

/* Traducción de .report-badge-{level} (report-components.css) */
const LEVEL: Record<string, string> = {
  success: 'bg-ok-soft text-ok',
  warning: 'bg-warn-2 text-warn-2-fg',
  info: 'bg-info-soft text-info-fg',
  danger: 'bg-danger-soft text-danger',
  neutral: 'bg-neutral-soft text-neutral-fg',
};

interface ReportBadgeProps {
  children: ReactNode;
  level?: ReportBadgeLevel;
}

export function ReportBadge({ children, level = 'neutral' }: ReportBadgeProps) {
  return (
    <span className={`inline-flex w-fit rounded-pill px-2 py-1 text-[10px] font-extrabold ${LEVEL[level] ?? LEVEL.neutral}`}>
      {children}
    </span>
  );
}
