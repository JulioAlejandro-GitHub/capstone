import type { ConfusionMatrix as ConfusionMatrixType } from '../types/api';

interface ConfusionMatrixProps {
  confusionMatrix: ConfusionMatrixType | null | undefined;
}

function valueOrDash(value: number | null | undefined) {
  return value === null || value === undefined ? '-' : value;
}

export function ConfusionMatrix({ confusionMatrix }: ConfusionMatrixProps) {
  const matrix = confusionMatrix?.matrix ?? [];
  const tn = confusionMatrix?.tn ?? matrix[0]?.[0] ?? null;
  const fp = confusionMatrix?.fp ?? matrix[0]?.[1] ?? null;
  const fn = confusionMatrix?.fn ?? matrix[1]?.[0] ?? null;
  const tp = confusionMatrix?.tp ?? matrix[1]?.[1] ?? null;

  return (
    <div className="confusion-matrix-wrap">
      <table className="confusion-matrix">
        <thead>
          <tr>
            <th>Real / Pred</th>
            <th>Pred uninfected</th>
            <th>Pred parasitized</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>Real uninfected</th>
            <td>
              <strong>{valueOrDash(tn)}</strong>
              <span>TN</span>
            </td>
            <td>
              <strong>{valueOrDash(fp)}</strong>
              <span>FP</span>
            </td>
          </tr>
          <tr>
            <th>Real parasitized</th>
            <td className="critical-cell">
              <strong>{valueOrDash(fn)}</strong>
              <span>FN</span>
            </td>
            <td>
              <strong>{valueOrDash(tp)}</strong>
              <span>TP</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p className="muted-text">
        FN representa celulas parasitadas clasificadas como uninfected y es el error
        experimental que requiere revision prioritaria.
      </p>
    </div>
  );
}
