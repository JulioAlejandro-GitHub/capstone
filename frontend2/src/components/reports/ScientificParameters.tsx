import type { ScientificParameters as Parameters } from '../../types/api';

const fields: ReadonlyArray<readonly [keyof Parameters, string, string]> = [
  ['target_recall', 'Sensibilidad objetivo', 'Sensibilidad clínica objetivo'],
  ['min_recall', 'Sensibilidad mínima', 'Sensibilidad mínima para selección'],
  ['calibrate_threshold', 'Calibrar umbral', 'Habilita calibración del umbral'],
  ['threshold', 'Umbral VALIDATION', 'Umbral aplicado en VALIDATION'],
  ['early_stopping_patience', 'Paciencia (épocas)', 'Épocas de paciencia'],
  ['early_stopping_min_delta', 'Mejora mínima', 'Mejora mínima requerida'],
  ['min_class_fraction', 'Fracción mínima por clase', 'Fracción mínima por clase (colapso)'],
  ['reject_prediction_collapse', 'Rechazar colapso de predicción', 'Rechazar predicciones colapsadas'],
  ['val_f2_parasitized', 'F2 VALIDATION', 'F2 clínico del checkpoint seleccionado'],
];

export function ScientificParameters({ parameters }: { parameters?: Parameters }) {
  return (
    <div className="min-w-0 max-w-full max-h-[88px] overflow-y-auto overflow-x-hidden rounded-lg border border-[#edf0f6] p-2 text-[11px] leading-[1.4]" role="region" aria-label="Parámetros científicos" tabIndex={0}>
      <dl className="m-0">
        {fields.map(([key, label, description]) => (
          <div key={key} className="grid grid-cols-[minmax(0,1fr) minmax(0,0.65fr)] gap-2 py-1 overflow-wrap-anywhere">
            <dt title={`${key}: ${description}`} className="text-fg-muted">{label}</dt>
            <dd className="m-0 text-right text-value tabular-nums">{parameters?.[key] == null ? '—' : String(parameters[key])}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
