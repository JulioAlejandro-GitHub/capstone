/** Célula seleccionada en la vista Entrenamiento: tipos y textos puros (sin red), compartidos por la escena y la página. */

export type CellCategory = 'true_positive' | 'true_negative' | 'false_positive' | 'false_negative';
export const CELL_CATEGORY_LABELS: Record<CellCategory, string> = {
  true_positive: 'Verdadero positivo', true_negative: 'Verdadero negativo', false_positive: 'Falso positivo', false_negative: 'Falso negativo',
};
export const cellCategory = ({ label, predicted }: { label: number | null; predicted: number | null }): CellCategory | null =>
  label == null || predicted == null ? null
    : label === 1 ? (predicted === 1 ? 'true_positive' : 'false_negative') : (predicted === 1 ? 'false_positive' : 'true_negative');
export const classText = (value: number | null | undefined) => value === 1 ? 'Parasitada' : value === 0 ? 'No parasitada' : 'Pendiente';
export const tracePng = (data: string) => `data:image/png;base64,${data}`;

/** Lo que la vista Entrenamiento muestra de la célula seleccionada (imagen de entrada y resultado de la predicción). */
export interface TrainingCell {
  sampleId: string; image: string; label: number | null; predicted: number | null; score: number; threshold: number | null;
  split: string; attemptId: string; category: CellCategory | null;
}

