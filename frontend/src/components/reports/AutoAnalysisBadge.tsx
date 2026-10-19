import type { RunAutoAnalysis } from '../../utils/runReport';
import { ReportBadge } from './ReportBadge';

interface AutoAnalysisBadgeProps {
  analysis: RunAutoAnalysis;
  showExploratoryNote?: boolean;
}

export function AutoAnalysisBadge({ analysis, showExploratoryNote = true }: AutoAnalysisBadgeProps) {
  return (
    <div className="report-analysis">
      <ReportBadge level={analysis.level}>{analysis.title}</ReportBadge>
      <p>{analysis.message}</p>
      {showExploratoryNote ? <small>Lectura automática exploratoria.</small> : null}
    </div>
  );
}
