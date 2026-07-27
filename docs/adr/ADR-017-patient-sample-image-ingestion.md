# ADR-017 — Identidad e ingesta segura de imágenes

Estado: aceptado — 2026-07-27

Se preservan binarios originales fuera de PostgreSQL, bajo una clave POSIX
relativa formada exclusivamente por UUID y checksum. La operación multipart
crea o resuelve sujeto, caso, muestra, frotis y lote dentro de la misma
transacción auditada; los movimientos ya realizados se compensan si falla la
base o el commit.

`users.id` identifica al actor JWT y nunca al paciente. `research_subjects.id`
es la identidad interna del sujeto y `subject_code` su pseudónimo visible.
Análogamente, `blood_samples.id` y `sample_code` identifican una muestra.
Identificadores externos se conservan en columnas separadas.

NIH-NLM fija cinco imágenes esperadas, conserva la carpeta como
`external_patient_id`, no inventa `external_sample_id`, genera una muestra
Capstone y usa un lote/frotis estable para reintentos.
