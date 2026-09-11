# E6 — Linaje exacto de EVALUATE / EXPLAIN

**Dictamen: NO APROBADA.** Implementación y pruebas locales realizadas; integración PostgreSQL, migración operativa y readiness E6 pendientes. La restricción de acceso al socket no implica que la BD esté caída. No se inicia E7.

## Línea base y procedencia

- Rama `main`; HEAD inicial y final `cd5c64d703358797570f5183dd598d93314dc0eb`.
- Entrega efectiva: árbol de trabajo sin commit, identificado por `etapa_6_manifiesto_2026-09-11.json`. No se efectuó reset, stash ni borrado de cambios previos.
- Al inicio ya estaban modificados `run_train_all_models.py`, `training/cli.py` y `test_migration_root_e4.py`. Existían sin seguimiento la migración E5, el paquete `execution`, sus dos suites y los informes/manifiestos E4–E5. Se preservaron.
- Manifiesto final E5 realmente disponible: **23 entradas**, las 23 concordantes al inicio de E6. El texto del pedido menciona 19/19 de un cierre previo; no se atribuye ese conteo al manifiesto actual. Después de E6 permanecen 22/23 idénticas: sólo se actualizó la expectativa de head en `test_migration_root_e4.py`. Migración y motor E5 intactos.
- Evidencia aportada por el usuario para E5: migración `20260912_01` instalada mediante wrapper, backup y preflight con rollback, 14 pruebas PostgreSQL aprobadas, `/ready` satisfactorio. Es evidencia de **E5**, no de este árbol modificado.
- Revisión operativa intentada en esta sesión: `docker compose exec -T backend python -m alembic current`. Resultado sanitizado: `permission denied while trying to connect to the docker API` sobre el socket local. No se pudo releer current ni `/ready`. No se cambió ningún permiso, servicio o instancia.

Se revisaron el contrato 0B v1.1, políticas de Alembic y seguridad de BD, cierres E1–E5, manifiesto final E5, repositorios de campañas/intentos/artefactos, resolutores, EVALUATE/EXPLAIN, calibración y masivos. También las rutas API de runs/predicciones/explicaciones y sus consumidores `frontend/src/services/api.ts` y `RunDetail.tsx`. No se encontraron instrucciones AGENTS adicionales aplicables en la inspección inicial.

## Cambio efectivo

Paquete `src/malaria_dl/assessment`: contrato canónico, resolución exacta, repositorio transaccional, servicio de ejecución/verificación, runtime Keras/Grad-CAM/LIME/SHAP y CLI. Nueva migración aditiva `20260912_02_assessments`, padre `20260912_01`, seis tablas, reservas únicas y triggers de identidad, propiedad, resultados, consumo de campaña e inmutabilidad.

E5 se resuelve desde el checkpoint **seleccionado y verificado**, no desde una lista ordenada de versiones. E6 conserva su UUID de versión y referencia al registro E5; deriva de manera estable el UUID del artefacto E6. La derivación está documentada y no se disfraza de backfill de `model_versions`/`artifacts`. La ruta legacy exige la fila real de artefacto, pertenencia al TRAIN, hash/tamaño y contrato original. No se inventa metadata de un histórico incompleto.

`dataset_integrity.materialized_relative_path` extrae la regla canónica de materialización de E1 para compartirla con el inventario E6 (incluye nombres repetidos por clase/split). No cambia el sello, los fingerprints ni los archivos. La revisión detectó un import local necesario tras la extracción; se corrigió y se ejecutó la suite E1. Las comprobaciones de entrada E3 se adaptaron al servicio activo E6, manteniendo el rechazo antes de carga/predict.

La calibración efectiva E5 usa `threshold_selected` y `threshold_used`; se exige concordancia, split val, clase positiva y checkpoint epoch coincidente. `clinical` sin prueba válida se rechaza. Los scores de E5 son brutos; no existe calibración implícita de probabilidades. La identidad registra el hash de la evidencia y la decisión efectiva. Un transformador de score no soportado se rechaza.

La reserva de identidad y cada lote usan transacciones cortas. Los resultados completos son inmutables. La verificación reconstruye métricas y hashes; sólo entonces finaliza el intento. Una petición equivalente activa no ejecuta; una verificada debe superar readback y comprobación de artefactos para reutilizarse. Cada intento posterior conserva lo anterior y tiene directorio distinto. La recuperación exige ausencia comprobada del proceso local; no se roba un propietario remoto o indeterminado.

EXPLAIN conserva la evaluación exacta, cuando se especifica, y valida modelo/muestras/contexto. Los tres métodos declaran score bruto. SHAP fija referencias acreditadas de train; los overlays usan RGB reconstruido a partir del contrato E3, y el cálculo usa el tensor transformado. Mapas/overlays son binarios exclusivos con UUID/hash/tamaño en BD; no hay resultados tabulares en archivos.

## Rutas retiradas y compatibilidad

- `run_evaluate_all_trainings.py` y `run_explain_all_trainings.py`: retirada la selección `DISTINCT ON ... ORDER BY mv.created_at DESC`; el inventario histórico muestra multiplicidad, el nuevo `main` exige campaña.
- `ModelVersionResolver`: retirado el orden por número de versión; la resolución por TRAIN sigue exigiendo exactamente una versión legacy.
- `evaluation/evaluator.py`: sustituido el main que escribía predicciones/matriz y resultados CSV por el servicio E6.
- `explainability/pipeline.py`: sustituido el main con directorio compartido/resumen CSV; `write_summary` rechaza su antiguo writer. Se preserva el cálculo Grad-CAM compartido con consulta histórica.
- `src.evaluate`, `src.explain`: conservan imports compatibles y propagan correctamente el código de salida del nuevo CLI.
- Constraint histórica de padre único por **child_run_id** conservada. No impedía varias evaluaciones distintas de un TRAIN. E6 no borra linaje ni duplica runs legacy artificialmente.
- API `/assessments` consultable con READ ONLY y paginación. Los endpoints y pantallas históricas conservan sus contratos; no pasan a mostrar resultados E6 como si fueran registros legacy. La consulta nueva se entrega por API, sin rediseño de frontend. No se modifica el flujo de publicación ni el servicio clínico de clasificación de imágenes subidas.

## Matriz de aceptación y evidencia

| Requisito / escenario | Cambio | Prueba / evidencia real | Límite |
|---|---|---|---|
| DATA-04; S03, S13 | Herencia E1 y rechazo de override, inventario desde asignaciones selladas | `test_accredited_sample_population_and_equivalent_override`, `test_dataset_override_rejected_before_verifier`, suite E1 | Fixtures sintéticos; no nueva comprobación operativa del dataset |
| PRE-02; S07, S22 | Contrato original E3, sin normalización doble | `test_minimal_model_uses_exact_e3_input` (Custom CNN, VGG nuevo/histórico, DenseNet), suite E3 | Modelos mínimos; no acreditación clínica/histórica por suposición |
| TRACE-02/03; S12, S13 | Versión/checkpoint exactos y pertenencia | `test_exact_e5_binding_and_cross_version_rejected`, `test_legacy_multiple_versions_rejected`, corrupción/carga y suite resolver | Vinculación SQL de campañas aún no ejecutada en PostgreSQL |
| EXEC-03; S12, S25 | Directorio exclusivo, temporales, binarios hash/tamaño, fallo conservado | `test_explanations_artifacts_separate_and_tamper_rejected`, `test_artifact_write_failure_never_verified` | No prueba de caída física de host |
| EVAL-03 | Identidad completa, reutilización y reserva activa | `test_exact_reuse_does_not_predict`, `test_identity_changes`, `test_active_response_no_predict`, corrupción | Locks/índices sólo pendientes de prueba PostgreSQL |
| TRACE-04; S30–S31 | Predicciones por muestra, métricas reconstruibles, lotes idempotentes y API | Locales de reconstrucción/reintento/API; `test_assessment_postgres.py` preparado | PostgreSQL NO VERIFICADO; mocks no acreditan persistencia |
| EVAL-01 | Desarrollo no TEST; bloqueo previo para final | Rechazo local; `test_final_requires_prior_exact_lock_and_synthetic_allow` preparado | Caso SQL positivo/negativo pendiente; E7 administrará los bloqueos |
| Campañas | Sólo intento aceptado E5, faltantes visibles, consumo explícito | Inspección local; `test_campaign_consumer_requires_exact_accepted_train` preparado | No campaña científica ejecutada |
| Recuperación / concurrencia | Propietario, reserva única, reintento separado y rechazo obsoleto | Locales de recuperación y error doble; tests PostgreSQL de dos conexiones y fencing preparados | No se acreditan locks por mocks ni incertidumbre de commit resuelta automáticamente |

## Pruebas realizadas

**Resultado final: 194 passed, 17 skipped, 17 warnings in 19.83s.** Las 17 omitidas corresponden a PostgreSQL E6. Las advertencias son de dependencias (protobuf, Alembic, NumPy/Keras y SHAP); no se ocultaron. Los resultados intermedios no se suman como si fueran casos distintos.

`ruff check` del paquete, migración, API y pruebas nuevas: aprobado. `git diff --check`: aprobado. Las pruebas nuevas usan UUID, bytes e imágenes sintéticos; los modelos mínimos sólo se guardan/cargan e infieren sobre esas imágenes, sin entrenamiento científico.

Comando local, desde `malaria_dl_local_project`:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider --tb=short \
  tests/test_assessment_e6.py tests/test_assessment_api_e6.py tests/test_assessment_postgres.py \
  tests/test_campaign_executor_e5.py tests/test_migration_root_e4.py \
  tests/test_run_evaluate_all_trainings.py tests/test_run_explain_all_trainings.py \
  tests/test_dataset_stage1.py tests/test_input_contract_e3.py tests/test_model_version_resolver.py \
  tests/test_evaluate_lineage_tracking.py tests/test_explain_lineage_tracking.py \
  tests/test_explain_threshold_integration.py tests/test_evaluation_training_lineage_service.py \
  tests/test_evaluation_training_lineage_migration.py
```

SQL offline generado con `MigrationContext(dialect_name='postgresql', as_sql=True)` y `Operations.context`; sin conexión, sin app config ni credenciales. Archivo temporal de revisión `/tmp/capstone_e6_reviewed.sql`, SHA-256 `c3dcf0a9aa8c89e18716b4cce2a74c4855708cf1efd8f1ebaa17a7feb3e3242e`. La prueba `test_e6_migration_renders_without_accidental_parameters` verifica el render y ausencia de binds accidentales. Este hash no es evidencia de ejecución de triggers.

## Persistencia, aislamiento y operación

`test_assessment_postgres.py`: 17 casos preparados, de ellos 16 sintéticos y una lectura de `public`. El fixture E4 crea únicamente un esquema con prefijo validado `capstone_test_...`; conserva transacción externa/savepoints y comprueba ausencia del esquema desde una conexión posterior incluso al fallar. Los casos de concurrencia y lectura posterior hacen commit sólo del esquema sintético y lo eliminan al finalizar. No hacen DELETE de eventos operativos ni desactivan triggers.

Los casos preparados cubren lotes idempotentes, conflicto, rechazo SQL de null, paciente inconsistente, propietario, conteos, explicación, consumo de campaña, dos conexiones y bloqueo TEST sintético. La lectura pública comprueba revisión `20260912_02`, seis tablas y ocho triggers habilitados. No acredita por sí sola todas las constraints de las tablas padre públicas, que son simplificadas en el fixture.

**No existe todavía evidencia E6 de rollback, commit entre conexiones ni concurrencia PostgreSQL ejecutada.** Se describe el aislamiento revisado y las aserciones preparadas, no un resultado supuesto. Tampoco se afirma durabilidad de un commit ante caída de host a partir de una prueba con rollback.

Comandos de integración sintética, wrapper de preflight/backup/migración y comprobación pública/readiness: [guía E6](../engineering/etapa_6_evaluate_explain_2026-09-11.md). No ejecutar la migración operativa antes de que pase la integración sintética.

## Limitaciones y dictamen

- **E6 bloqueante:** PostgreSQL, instalación de `20260912_02`, triggers operativos y readiness pendientes por acceso al socket. El render offline y las pruebas locales no levantan este bloqueo.
- Históricos: se conservan consultables; los incompletos no se ejecutan por suposición. No se migraron calibradores de probabilidad históricos ni se inventaron bindings. El consumidor acepta calibración de umbral E5 sobre scores brutos.
- Recuperación: reinicia por intento, sin concatenar parciales; propietarios remotos/indeterminados requieren diagnóstico. No se borran automáticamente archivos huérfanos. La prueba de crash físico/commit incierto no se presenta como realizada.
- E7: gestión del bloqueo final de candidatos, comparación/ranking/análisis estadístico. Sin acceso operativo a TEST en esta etapa.
- Frontend: consulta histórica preservada; nueva evidencia E6 consultable mediante API. No se entrega rediseño de pantallas ni regeneración legacy de artefactos E6.

No se modificaron dataset, split, imágenes originales, checkpoints históricos, campañas congeladas ni producción. No se ejecutaron campañas científicas ni inferencias sobre TEST operativo. Los resultados estructurados nuevos no tienen CSV ni fallback de archivos. La eventual aprobación técnica no acreditará desempeño clínico. **E6 sigue NO APROBADA y E7 no se inicia.**
