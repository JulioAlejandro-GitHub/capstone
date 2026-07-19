export type RunProcessKind = 'training' | 'evaluation' | 'explainability';

const PROCESS_LABELS: Record<RunProcessKind, string> = {
  training: 'TRAIN',
  evaluation: 'EVALUATE',
  explainability: 'EXPLAIN',
};

interface RunProcessBadgeProps {
  kind: RunProcessKind;
}

export function RunProcessBadge({ kind }: RunProcessBadgeProps) {
  return (
    <span className={`run-process-badge run-process-badge--${kind}`}>
      {PROCESS_LABELS[kind]}
    </span>
  );
}
