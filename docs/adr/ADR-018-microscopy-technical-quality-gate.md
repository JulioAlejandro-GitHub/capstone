# ADR-018: quality gate técnico para microscopía

Estado: aceptado. Fecha: 2026-07-27.

Se crean `microscopy_analysis_runs` separados de los runs de entrenamiento. Cada
run congela imágenes y perfil, y registra un manifiesto SHA-256 canónico. El gate
solo mide integridad y calidad técnica; no diagnostica, segmenta, detecta ni
clasifica. `pass` habilita, `warning` exige revisión autorizada y `fail` bloquea
sin posibilidad de aprobación manual. Originales, evaluaciones, eventos y
decisiones mantienen trazabilidad append-only.
