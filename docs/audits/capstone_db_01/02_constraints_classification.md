# CAPSTONE-DB-01 — Clasificación de restricciones

Estado documental: `HISTORICAL_AUDIT` — 2026-10-12. Ninguna restricción modificada.

## Método y cobertura

Se exportaron las 967 constraints y 1.515 definiciones de columna de tablas. [constraints_classification.csv](constraints_classification.csv) registra nombre, tipo, ubicación, definición, consumidores por relación, finalidad, categoría, evidencia, riesgo y recomendación. Las rutinas y triggers tienen inventarios equivalentes. El SQL vigente sustenta la clasificación; ni el nombre `legacy` ni un estado FROZEN bastan para declarar obsolescencia.

La clasificación estructural está completa. La clasificación semántica es **PARCIAL**: los grupos B generales son conservadores, basados en la expresión y dominio de evidencia; no se certificó individualmente la necesidad de cada constante o política. D identifica decisiones pendientes. No usar el CSV como lista automática de eliminación. Los consumidores indirectos deben contrastarse con [04_code_dependencies.md](04_code_dependencies.md) y el cuerpo de las funciones.

| Inventario | A | B | C | D |
|---|---:|---:|---:|---:|
| pg_constraint | 536 | 389 | 0 | 42 |
| Funciones de aplicación | 3 | 68 | 0 | 9 |
| Triggers de aplicación | 0 | 100 | 0 | 7 |

Además: 1.515 contratos de columna categoría A; 1.016 triggers internos de integridad categoría A. Las filas C comprobadas son controles de código o **subcondiciones** de funciones mixtas, descritos abajo; no implican que se deba eliminar la función completa. Diez filas pg_constraint de tipo `t` remiten a triggers con clasificación más específica.

## Decisiones sustentadas

| Control y ubicación | Finalidad/evidencia | Categoría | Riesgo y recomendación |
|---|---|---|---|
| PK, FK, UNIQUE, tipos y NOT NULL | Identidad, referencias válidas, obligatoriedad; definiciones reales con ON DELETE/UPDATE en inventario | A | Alto si se eliminan. Conservar; no convertir RESTRICT/CASCADE sin análisis del grafo. |
| `enforce_dataset_assignment_consistency`, protect_frozen_dataset_* | Coherencia paciente/clase/asignación y separación de splits; cuerpos comparan identidades y particiones | B | Conservar: evita fuga entre TRAIN/VAL/TEST y mutación de datos científicos. |
| `enforce_model_version_governance`, `protect_governed_artifact_identity` | Identidad de TRAIN, checkpoint, hash y contenido gobernado | B | Conservar; la inmutabilidad no es una restricción histórica de Alembic. |
| `enforce_run_lineage_governance` | Tipos parent/child y referencias de model_version/checkpoint | B | Conservar. DB-03 no demuestra que este trigger esté bloqueando EXPLAIN E6. |
| `assessment_identity_guard`, `assessment_result_guard`, `assessment_attempt_guard` | TRAIN, muestras, paciente, propietario, completitud y acceso final a TEST | B | Conservar. Estados de intentos verificables protegen evidencia y recuperación. |
| train_event_guard, train_record_guard, train_session_guard | Propietario, secuencia contigua, identidad y cierre verificable | B | Conservar semántica y transacción; retirar comprobaciones históricas de versión en consumidores. |
| v2_binary_metric_guard, v2_evaluation_complete, e04_assert_calibration | Relación métricas-evaluación-TRAIN, calibración, eventos y checkpoints | B | Conservar. Nombres v2/e04 no prueban obsolescencia. |
| v2_xai_* y dbv21_xai_* | Concordancia modelo, imagen, muestra, método, background SHAP y artefactos | B | Conservar. No inferir que una tabla actualmente vacía implica desuso permanente. |
| Validadores celulares, snapshots y eventos append-only | Coherencia detección→crop→clasificación→explicación→revisión; hashes y estados finales | B | Conservar; impiden reinterpretar resultados con otro modelo/entrada. |
| `campaign_guard`: identidad, hash, matriz y evidencia dataset | Compara contrato persistido, matriz y evidencia; trigger en experimental_campaigns | B | Conservar controles de fondo; el guard completo queda D por reglas mixtas. |
| `campaign_guard`: `integrity_status = 'verified'` exclusivamente | Productor actual emite verified_requested_splits para train/val; nueve evidencias exitosas de campaigns.configure en ese estado | C, subcondición | Corregir aceptación de evidencia suficiente por splits, manteniendo éxito, versión y snapshot. No eliminar comprobación de evidencia. |
| `campaign_guard`: transiciones, no DELETE, `first_verified_attempt`, checkpoint 0.5 y constantes de protocolo | Política explícita en cuerpo SQL; no se demostró que todas sean artificiales | D | Analizar necesidad científica y operativa por regla antes de simplificar. |
| campaign_technical_guard / controlled_pause_guard | Exige campaña paused y contratos específicos de ejecución controlada, incluyendo excepción Darwin/arm64/CPU/float32 | D | Puede ser política temporal; comprobar consumidores controlled.py/local_execution y estados activos antes de proponer eliminación. |
| controlled_binding_guard / controlled_run_guard / train_revision_binding_guard | Consistencia campaña-intento-sesión-run-entorno | B | Conservar integridad aunque se simplifique el modo controlado. |
| experiment_require_owner / experiment_reservation_guard | Propiedad exclusiva y exclusión de TRAIN frente a assessment activo | B | Conservar protección transaccional; evaluar separadamente capacidad/concurrencia futura. |
| e04_legacy_admission | Solo migrator puede insertar source_kind=legacy | D | No es comparación de revisión; impide fabricar evidencia histórica. Investigar escrituras/importaciones antes de retirar. |
| execution/schema.py: SUPPORTED_REVISIONS y require_e10_schema | Rechaza revisión instalada pese a capacidades E10/v2 satisfechas | C | Eliminar dependencia histórica con consumidores; no ampliar whitelist como solución definitiva. |
| schema_contract.py: hashes/listas exactas del baseline | Detecta cambios de implementación; actualmente coincide | D | Bajo política de esquema único, revisar/simplificar pinning sin perder semántica de integridad. No se demostró fallo actual de este control. |
| Comparaciones `revision == V2_REVISION` en repositorios/resultados | Seleccionan contratos de escritura/lectura antiguos o actuales por etiqueta de Alembic | C | Adoptar directamente persistencia actual; riesgo alto si solo se elimina el rechazo inicial. |
| `schema_version` de eventos/configuración/snapshots | Contrato de contenido, no versión del esquema SQL | B cuando valida identidad/forma científica | Conservar salvo evidencia concreta de redundancia. |
| database_safety.py: destino, esquemas protegidos | Previene operar sobre otra base o destruir public | A | Conservar; la política de no retrocompatibilidad no autoriza retirar protecciones de destino. |

No se recomienda DROP de un trigger concreto en esta fase. Los candidatos demostrados son selecciones históricas en Python y una condición desactualizada dentro de campaign_guard. El resto requiere decisiones por regla, no limpieza por coincidencia textual.
