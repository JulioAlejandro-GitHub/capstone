/** GET /runs/{id}/training-trajectories: score VAL de cada célula en cada época, tal como lo registró TRAIN. */
export interface TrajectoryEpoch { epoch: number; phase: string }
export interface TrajectorySample { sample: string; label: 0 | 1; sample_id: string | null }
export interface TrainingTrajectories {
  training_run_id: string;
  state: 'available' | 'missing' | 'inconsistent';
  issues: string[];
  epochs: TrajectoryEpoch[];
  samples: TrajectorySample[];
  /** Una fila por muestra, una columna por época (mismo orden que `epochs`). */
  scores: (number | null)[][];
  training_threshold: number;
  evaluation_attempt_id: string | null;
}
