import type { ReactNode } from 'react';

import type { RunAnalysisLevel } from '../../utils/runReport';

interface ReportBadgeProps {
  children: ReactNode;
  level?: RunAnalysisLevel;
}

export function ReportBadge({ children, level = 'neutral' }: ReportBadgeProps) {
  return <span className={`report-badge report-badge-${level}`}>{children}</span>;
}
