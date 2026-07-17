import type { RunConfusionCounts } from '../../utils/runReport';

interface MiniConfusionMatrixProps {
  counts: RunConfusionCounts;
}

const countFormatter = new Intl.NumberFormat('es-CL', {
  maximumFractionDigits: 0,
});

function MatrixValue({ code, value }: { code: 'TN' | 'FP' | 'FN' | 'TP'; value: number | null }) {
  const kind = code === 'FP' || code === 'FN' ? 'error' : 'correct';
  return (
    <td className={`mini-confusion-matrix__cell mini-confusion-matrix__cell--${kind}`}>
      <span>{code}</span>
      <strong>{value === null ? '-' : countFormatter.format(value)}</strong>
    </td>
  );
}

export function MiniConfusionMatrix({ counts }: MiniConfusionMatrixProps) {
  const hasValues = Object.values(counts).some((value) => value !== null);
  if (!hasValues) {
    return <div className="mini-confusion-matrix mini-confusion-matrix--empty">Sin matriz</div>;
  }

  return (
    <div className="mini-confusion-matrix">
      <table aria-label="Matriz de confusión resumida">
        <caption className="report-sr-only">
          Filas de clase real y columnas de clase predicha
        </caption>
        <thead>
          <tr>
            <th aria-hidden="true" />
            <th scope="col">Pred U</th>
            <th scope="col">Pred P</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Real U</th>
            <MatrixValue code="TN" value={counts.tn} />
            <MatrixValue code="FP" value={counts.fp} />
          </tr>
          <tr>
            <th scope="row">Real P</th>
            <MatrixValue code="FN" value={counts.fn} />
            <MatrixValue code="TP" value={counts.tp} />
          </tr>
        </tbody>
      </table>
    </div>
  );
}
