import type { RunAutoAnalysis } from '../../utils/runReport';
import { ReportBadge } from './ReportBadge';

interface AutoAnalysisBadgeProps {
  analysis: RunAutoAnalysis;
}

export function AutoAnalysisBadge({ analysis }: AutoAnalysisBadgeProps) {
  return (
    <div className="report-analysis">
      <ReportBadge level={analysis.level}>{analysis.title}</ReportBadge>
      <p>{analysis.message}</p>
      <small>Lectura automática exploratoria.</small>
    </div>
  );
}
