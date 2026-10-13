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
    <div className="run-scientific-parameters" role="region" aria-label="Parámetros científicos" tabIndex={0}>
      <dl>
        {fields.map(([key, label, description]) => (
          <div className="run-scientific-parameters__entry" key={key}>
            <dt title={`${key}: ${description}`}>{label}</dt>
            <dd>{parameters?.[key] == null ? '—' : String(parameters[key])}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
