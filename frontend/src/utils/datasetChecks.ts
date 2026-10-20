const checkLabels: Record<string, string> = {
  identity_coverage: 'Cobertura de identidad',
  identity_conflicts: 'Conflictos de identidad',
  patient_train_val_overlap: 'Pacientes compartidos TRAIN / VAL',
  patient_train_test_overlap: 'Pacientes compartidos TRAIN / TEST',
  patient_val_test_overlap: 'Pacientes compartidos VAL / TEST',
  duplicate_cross_split_overlap: 'Duplicados entre conjuntos',
  assignment_count: 'Asignaciones completas',
  source_record_count: 'Registros fuente completos',
  split_completeness: 'Completitud del split',
  class_presence_train: 'Clases presentes en TRAIN',
  class_presence_val: 'Clases presentes en VAL',
  class_presence_test: 'Clases presentes en TEST',
};

export function datasetCheckLabel(name: string): string {
  return Object.hasOwn(checkLabels, name) ? checkLabels[name] : name;
}
