# DBV2.2 — BLOCKED

DBV2.2 BLOCKED — DBV2.1 CONTRACT CONFLICT

El modelo aprobado (`../dbv2_1_xai_model.md`, sección Métricas, N:M y congelación) exige insertar evaluación y miembros en una transacción, con validación diferida. El SQL aprobado declara las tablas con `xai_quantitative_evaluations.id` y `xai_evaluation_members.evaluation_id`, sin el otro campo (líneas 242 y 252; las declaraciones exactas también constan en el CSV de columnas).

Sin embargo, `../dbv2_1_target_schema.sql:2834` contiene en `dbv21_xai_evaluation_complete`:

```sql
eid:=CASE WHEN TG_TABLE_NAME='xai_quantitative_evaluations' THEN NEW.id ELSE NEW.evaluation_id END;
```

Los triggers de las líneas 5489 y 5491 conectan esa función a ambas tablas. PostgreSQL resuelve los campos de ambas ramas de la expresión antes de seleccionar el resultado. La reproducción mínima en PostgreSQL 17.9 devuelve:

- xai_quantitative_evaluations: SQLSTATE 42703, `record "new" has no field "evaluation_id"`.
- xai_evaluation_members: SQLSTATE 42703, `record "new" has no field "id"`.

Por tanto, materializar literalmente este SQL no permite la inserción N:M válida exigida por el documento XAI. Corregirlo silenciosamente produciría una función distinta de la aprobada. Se detiene DBV2.2 por las secciones 5 y 33 de la solicitud.

Resolución propuesta para decisión explícita: sustituir la expresión CASE por un IF/ELSE PL/pgSQL con una asignación separada por tabla, aprobar la corrección de DBV2.1 y revalidar sus artefactos. No se aplicó esa propuesta ni se certificó su implementación.

La baseline candidata permanece intacta: revision `pg_v2_baseline`, down_revision `None`, una revisión en versions. No se construyó ni certificó la baseline DBV2.2. No se ejecutó el SQL de diseño, ninguna migración legacy, adoption, transferencia, TRAIN/EVALUATE/EXPLAIN o cutover. Cero conexiones y cero escrituras en PostgreSQL operacional.

Prueba ejecutada: reproducción mínima transaccional de la expresión conflictiva, no instalación de BD-v2. Se conservan SQL, log, identidad e inspección del contenedor. El esquema de prueba fue revertido completamente.

GATE DBV2.2: BLOCKED. No se solicita aprobación de certificación. Requiere resolver explícitamente el conflicto DBV2.1 antes de reanudar y, después de certificar, solicitar GATE DBV2.2. No iniciar la fase siguiente.
