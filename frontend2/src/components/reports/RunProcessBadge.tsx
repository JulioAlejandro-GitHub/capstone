export type RunProcessKind = 'training' | 'evaluation' | 'explainability';

const PROCESS_LABELS: Record<RunProcessKind, string> = {
  training: 'TRAIN',
  evaluation: 'EVALUATE',
  explainability: 'EXPLAIN',
};

/* Traducción de .run-process-badge--{kind} */
const TONE: Record<RunProcessKind, string> = {
  training: 'border-[#c9d7f2] bg-[#eaf0ff] text-accent',
  evaluation: 'border-[#d8cef5] bg-[#f1edff] text-[#6045a5]',
  explainability: 'border-[#bfe4df] bg-[#e8f8f5] text-[#176b61]',
};

interface RunProcessBadgeProps {
  kind: RunProcessKind;
}

export function RunProcessBadge({ kind }: RunProcessBadgeProps) {
  return (
    <span className={`inline-flex w-fit items-center border border-transparent rounded-md px-1.75 py-0.75 text-[9px] font-black leading-[1.2] tracking-[0.09em] ${TONE[kind]}`}>
      {PROCESS_LABELS[kind]}
    </span>
  );
}
