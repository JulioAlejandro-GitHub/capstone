import { useId } from 'react';

import type { ConfusionMatrix as ConfusionMatrixType } from '../types/api';

interface ConfusionMatrixProps {
  confusionMatrix: ConfusionMatrixType | null | undefined;
  showPercentages?: boolean;
}

type CellDefinition = {
  code: 'TN' | 'FP' | 'FN' | 'TP';
  name: string;
  value: number | null;
  result: 'correct' | 'error';
  priority?: boolean;
};

/* .clinical-confusion__cell (base) — padding 12px, @≤640px 10px 8px, radius 10px */
const CELL_BASE_CLASS =
  'relative min-w-0 p-3 max-sm:px-2 max-sm:py-2.5 rounded-step border text-center align-top';

/* .clinical-confusion__cell--correct / --error / --priority (4 combinaciones reales) */
const CELL_CLASS: Record<string, string> = {
  correct: 'border-[#cfd7e8] border-l-[4px] border-l-[#3f7f62] bg-subtle',
  error: 'border-[#cfd7e8] border-dashed border-l-[4px] border-l-[#b56b22] bg-[#fffaf0]',
  'correct-priority': 'border-[#9e3f3f] border-l-[4px] border-l-[#9e3f3f] bg-[#fff6f6]',
  'error-priority': 'border-[#9e3f3f] border-dashed border-l-[4px] border-l-[#9e3f3f] bg-[#fff6f6]',
};

const countFormatter = new Intl.NumberFormat('es-CL', {
  maximumFractionDigits: 2,
});

const percentageFormatter = new Intl.NumberFormat('es-CL', {
  maximumFractionDigits: 1,
  minimumFractionDigits: 1,
});

function normalizedCount(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const numericValue = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numericValue) && numericValue >= 0 ? numericValue : null;
}

function resolvedCount(explicitValue: unknown, matrixValue: unknown) {
  return normalizedCount(explicitValue) ?? normalizedCount(matrixValue);
}

function labelOrFallback(label: string | undefined, fallback: string) {
  const normalizedLabel = label?.trim();
  return normalizedLabel || fallback;
}

function formattedCount(value: number | null) {
  return value === null ? 'Sin dato' : countFormatter.format(value);
}

function formattedPercentage(value: number, total: number) {
  return `${percentageFormatter.format((value / total) * 100)} %`;
}

function cellClass(cell: CellDefinition) {
  if (cell.priority) {
    return cell.result === 'error' ? CELL_CLASS['error-priority'] : CELL_CLASS['correct-priority'];
  }
  return CELL_CLASS[cell.result];
}

function MatrixCell({
  cell,
  total,
  showPercentages,
}: {
  cell: CellDefinition;
  total: number | null;
  showPercentages: boolean;
}) {
  const hasPercentage = showPercentages && cell.value !== null && total !== null;

  return (
    <td
      className={`${CELL_BASE_CLASS} ${cellClass(cell)}`}
      data-result={cell.result === 'correct' ? 'Acierto' : 'Error'}
    >
      <span className="block text-[10px] font-extrabold tracking-[0.08em] uppercase text-[#52617e]">
        {cell.result === 'correct' ? 'Acierto' : 'Error'}
      </span>
      <strong className="block my-[3px] text-[clamp(20px,3vw,28px)] leading-[1.1] text-[#17223b]">{formattedCount(cell.value)}</strong>
      <span className="block text-[11px] leading-[1.35] text-[#52617e]">
        <abbr className="text-ink font-extrabold no-underline" title={cell.name}>{cell.code}</abbr> · {cell.name}
      </span>
      {hasPercentage ? (
        <span className="block mt-1 text-[11px] leading-[1.35] tabular-nums text-[#52617e]">
          {formattedPercentage(cell.value as number, total as number)} del total
        </span>
      ) : null}
    </td>
  );
}

export function ConfusionMatrix({
  confusionMatrix,
  showPercentages = true,
}: ConfusionMatrixProps) {
  const descriptionId = useId();
  const matrix = confusionMatrix?.matrix ?? [];
  const negativeLabel = labelOrFallback(confusionMatrix?.labels?.[0], 'uninfected');
  const positiveLabel = labelOrFallback(confusionMatrix?.labels?.[1], 'parasitized');

  const tn = resolvedCount(confusionMatrix?.tn, matrix[0]?.[0]);
  const fp = resolvedCount(confusionMatrix?.fp, matrix[0]?.[1]);
  const fn = resolvedCount(confusionMatrix?.fn, matrix[1]?.[0]);
  const tp = resolvedCount(confusionMatrix?.tp, matrix[1]?.[1]);
  const counts = [tn, fp, fn, tp];
  const availableCount = counts.filter((value) => value !== null).length;
  const isComplete = availableCount === counts.length;
  const rawTotal = isComplete
    ? counts.reduce<number>((sum, value) => sum + (value ?? 0), 0)
    : null;
  const total = rawTotal !== null && rawTotal > 0 ? rawTotal : null;

  if (availableCount === 0) {
    return (
      <div className="grid gap-3 justify-items-start m-0 p-3 rounded-step border border-dashed border-[#aeb9ce] text-[13px] text-[#52617e]" role="status">
        <strong className="text-ink">Matriz no disponible</strong>
        <span>No hay conteos TN, FP, FN o TP registrados para esta ejecución.</span>
      </div>
    );
  }

  const correctTotal = isComplete ? (tn ?? 0) + (tp ?? 0) : null;
  const errorTotal = isComplete ? (fp ?? 0) + (fn ?? 0) : null;
  const cellDefinitions: CellDefinition[] = [
    { code: 'TN', name: 'Verdadero negativo', value: tn, result: 'correct' },
    { code: 'FP', name: 'Falso positivo', value: fp, result: 'error' },
    {
      code: 'FN',
      name: 'Falso negativo',
      value: fn,
      result: 'error',
      priority: true,
    },
    { code: 'TP', name: 'Verdadero positivo', value: tp, result: 'correct' },
  ];

  return (
    <figure className="grid gap-3 m-0" aria-describedby={descriptionId}>
      <div className="max-w-[760px] overflow-x-auto">
        <table className="w-full min-w-[520px] max-sm:min-w-[460px] table-fixed border-collapse border-spacing-[6px]">
          <caption className="px-0 pb-1.5 text-xs text-muted text-left">Filas: clase real · Columnas: predicción del modelo</caption>
          <thead>
            <tr>
              <th scope="col" className="w-[30%] px-2.5 py-2 text-xs text-ink font-bold leading-[1.35] text-left">Real ↓ / Predicción →</th>
              <th scope="col" className="px-2.5 py-2 text-xs text-ink font-bold leading-[1.35] text-center">Pred. {negativeLabel}</th>
              <th scope="col" className="px-2.5 py-2 text-xs text-ink font-bold leading-[1.35] text-center">Pred. {positiveLabel}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row" className="w-[30%] px-2.5 py-2 text-xs text-ink font-bold leading-[1.35] text-left">Real {negativeLabel}</th>
              <MatrixCell
                cell={cellDefinitions[0]}
                total={total}
                showPercentages={showPercentages}
              />
              <MatrixCell
                cell={cellDefinitions[1]}
                total={total}
                showPercentages={showPercentages}
              />
            </tr>
            <tr>
              <th scope="row" className="w-[30%] px-2.5 py-2 text-xs text-ink font-bold leading-[1.35] text-left">Real {positiveLabel}</th>
              <MatrixCell
                cell={cellDefinitions[2]}
                total={total}
                showPercentages={showPercentages}
              />
              <MatrixCell
                cell={cellDefinitions[3]}
                total={total}
                showPercentages={showPercentages}
              />
            </tr>
          </tbody>
        </table>
      </div>

      {!isComplete || total === null ? (
        <p className="m-0 max-w-[760px] px-2.5 py-2 border-l-[3px] border-l-[#92702c] bg-[#fffaf0] text-xs leading-[1.45] text-[#52617e]" role="note">
          {!isComplete
            ? 'La matriz está incompleta; los porcentajes se omiten para evitar una interpretación engañosa.'
            : 'La matriz no contiene observaciones; no es posible calcular porcentajes.'}
        </p>
      ) : null}

      <figcaption id={descriptionId} className="grid max-w-[760px] gap-1.5 text-xs leading-[1.45] text-[#3d4963]">
        {correctTotal !== null && errorTotal !== null ? (
          <p className="m-0 text-xs leading-[1.45] text-[#52617e]">
            <strong>Resumen:</strong> {countFormatter.format(correctTotal)} aciertos y{' '}
            {countFormatter.format(errorTotal)} errores sobre {countFormatter.format(rawTotal ?? 0)}
            {showPercentages && total !== null
              ? ` (${formattedPercentage(errorTotal, total)} de error)`
              : ''}.
          </p>
        ) : null}
        <ul className="grid gap-1 m-0 pl-[19px]">
          <li>
            <strong>FP — {formattedCount(fp)}:</strong> células {negativeLabel} clasificadas
            como {positiveLabel}; pueden aumentar las revisiones innecesarias.
          </li>
          <li>
            <strong className="text-[#8b3030]">FN — {formattedCount(fn)}:</strong> células {positiveLabel} clasificadas
            como {negativeLabel}; requieren revisión prioritaria por tratarse de casos
            positivos no detectados.
          </li>
        </ul>
      </figcaption>
    </figure>
  );
}
