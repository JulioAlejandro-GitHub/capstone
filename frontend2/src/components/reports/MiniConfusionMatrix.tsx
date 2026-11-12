import type { RunConfusionCounts } from '../../utils/runReport';

interface MiniConfusionMatrixProps {
  counts: RunConfusionCounts;
  emptyLabel?: string;
}

/* .mini-confusion-matrix th/td (border 0, padding 3px, centrado) */
const CELL_BASE_CLASS = 'border-0 p-[3px] text-center align-middle';

/* .mini-confusion-matrix__cell + --error */
const CELL_CLASS: Record<string, string> = {
  correct: 'rounded-[7px] bg-[#edf8f2] text-ok',
  error: 'rounded-[7px] bg-[#fff2e2] text-[#8a4c00]',
};

const countFormatter = new Intl.NumberFormat('es-CL', {
  maximumFractionDigits: 0,
});

function MatrixValue({ code, value }: { code: 'TN' | 'FP' | 'FN' | 'TP'; value: number | null }) {
  const kind = code === 'FP' || code === 'FN' ? 'error' : 'correct';
  return (
    <td className={`${CELL_BASE_CLASS} ${CELL_CLASS[kind]}`}>
      <span className="block text-[9px] font-extrabold">{code}</span>
      <strong className="block mt-px text-xs tabular-nums">{value === null ? '-' : countFormatter.format(value)}</strong>
    </td>
  );
}

export function MiniConfusionMatrix({
  counts,
  emptyLabel = 'Sin matriz',
}: MiniConfusionMatrixProps) {
  const hasValues = Object.values(counts).some((value) => value !== null);
  if (!hasValues) {
    return (
      <div className="grid min-h-[90px] place-items-center border border-dashed border-border-strong rounded-[9px] text-[11px] text-muted-2" role="status">
        {emptyLabel}
      </div>
    );
  }

  return (
    <div className="min-w-0">
      <table className="w-full table-fixed border-collapse border-spacing-[3px]" aria-label="Matriz de confusión resumida">
        <caption className="sr-only">
          Filas de clase real y columnas de clase predicha
        </caption>
        <thead>
          <tr>
            <th aria-hidden="true" className="border-0 p-[3px] text-center align-middle text-[#75829b] text-[9px] font-extrabold" />
            <th scope="col" className="border-0 p-[3px] text-center align-middle text-[#75829b] text-[9px] font-extrabold">Pred U</th>
            <th scope="col" className="border-0 p-[3px] text-center align-middle text-[#75829b] text-[9px] font-extrabold">Pred P</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row" className="border-0 p-[3px] text-center align-middle text-[#75829b] text-[9px] font-extrabold">Real U</th>
            <MatrixValue code="TN" value={counts.tn} />
            <MatrixValue code="FP" value={counts.fp} />
          </tr>
          <tr>
            <th scope="row" className="border-0 p-[3px] text-center align-middle text-[#75829b] text-[9px] font-extrabold">Real P</th>
            <MatrixValue code="FN" value={counts.fn} />
            <MatrixValue code="TP" value={counts.tp} />
          </tr>
        </tbody>
      </table>
    </div>
  );
}
