import type { RunLineageConfidence } from '../../types/api';
import { ReportBadge, type ReportBadgeLevel } from './ReportBadge';

interface LineagePresentation {
  label: string;
  level: ReportBadgeLevel;
}

const PRESENTATIONS: Record<RunLineageConfidence, LineagePresentation> = {
  explicit: { label: 'Linaje explícito', level: 'success' },
  inferred_exact_checkpoint: { label: 'Inferido por checkpoint', level: 'info' },
  inferred_model_version: { label: 'Inferido por versión', level: 'info' },
  inferred_heuristic: { label: 'Inferido heurístico', level: 'warning' },
  unknown: { label: 'Linaje desconocido', level: 'danger' },
};

interface LineageBadgeProps {
  confidence: RunLineageConfidence | null | undefined;
}

export function LineageBadge({ confidence }: LineageBadgeProps) {
  const presentation = confidence
    ? (PRESENTATIONS[confidence] || PRESENTATIONS.unknown)
    : { label: 'Sin linaje', level: 'neutral' as const };

  return <ReportBadge level={presentation.level}>{presentation.label}</ReportBadge>;
}
