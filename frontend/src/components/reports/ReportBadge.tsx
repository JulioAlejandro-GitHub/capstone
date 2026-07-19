import type { ReactNode } from 'react';

import type { RunAnalysisLevel } from '../../utils/runReport';

export type ReportBadgeLevel = RunAnalysisLevel | 'info';

interface ReportBadgeProps {
  children: ReactNode;
  level?: ReportBadgeLevel;
}

export function ReportBadge({ children, level = 'neutral' }: ReportBadgeProps) {
  return <span className={`report-badge report-badge-${level}`}>{children}</span>;
}
