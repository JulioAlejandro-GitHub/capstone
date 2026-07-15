import { useId } from 'react';

import type { ConfusionMatrix as ConfusionMatrixType } from '../types/api';
import './ConfusionMatrix.css';

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
      className={`clinical-confusion__cell clinical-confusion__cell--${cell.result}${cell.priority ? ' clinical-confusion__cell--priority' : ''}`}
      data-result={cell.result === 'correct' ? 'Acierto' : 'Error'}
    >
      <span className="clinical-confusion__result">
        {cell.result === 'correct' ? 'Acierto' : 'Error'}
      </span>
      <strong className="clinical-confusion__value">{formattedCount(cell.value)}</strong>
      <span className="clinical-confusion__code">
        <abbr title={cell.name}>{cell.code}</abbr> · {cell.name}
      </span>
      {hasPercentage ? (
        <span className="clinical-confusion__percentage">
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
      <div className="clinical-confusion clinical-confusion--empty" role="status">
        <strong>Matriz no disponible</strong>
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
    <figure className="clinical-confusion" aria-describedby={descriptionId}>
      <div className="clinical-confusion__table-scroll">
        <table className="clinical-confusion__table">
          <caption>Filas: clase real · Columnas: predicción del modelo</caption>
          <thead>
            <tr>
              <th scope="col">Real ↓ / Predicción →</th>
              <th scope="col">Pred. {negativeLabel}</th>
              <th scope="col">Pred. {positiveLabel}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Real {negativeLabel}</th>
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
              <th scope="row">Real {positiveLabel}</th>
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
        <p className="clinical-confusion__data-note" role="note">
          {!isComplete
            ? 'La matriz está incompleta; los porcentajes se omiten para evitar una interpretación engañosa.'
            : 'La matriz no contiene observaciones; no es posible calcular porcentajes.'}
        </p>
      ) : null}

      <figcaption id={descriptionId} className="clinical-confusion__interpretation">
        {correctTotal !== null && errorTotal !== null ? (
          <p className="clinical-confusion__summary">
            <strong>Resumen:</strong> {countFormatter.format(correctTotal)} aciertos y{' '}
            {countFormatter.format(errorTotal)} errores sobre {countFormatter.format(rawTotal ?? 0)}
            {showPercentages && total !== null
              ? ` (${formattedPercentage(errorTotal, total)} de error)`
              : ''}.
          </p>
        ) : null}
        <ul>
          <li>
            <strong>FP — {formattedCount(fp)}:</strong> células {negativeLabel} clasificadas
            como {positiveLabel}; pueden aumentar las revisiones innecesarias.
          </li>
          <li className="clinical-confusion__priority-note">
            <strong>FN — {formattedCount(fn)}:</strong> células {positiveLabel} clasificadas
            como {negativeLabel}; requieren revisión prioritaria por tratarse de casos
            positivos no detectados.
          </li>
        </ul>
      </figcaption>
    </figure>
  );
}
