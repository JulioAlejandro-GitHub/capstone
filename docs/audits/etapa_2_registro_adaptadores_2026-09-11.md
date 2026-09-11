# E2 — Registro único, adaptadores y configuración

Fecha: 2026-09-11. **Dictamen: NO APROBADA — integración PostgreSQL de E2 pendiente.**

## 1. Línea base y alcance

Commit inicial: `b6cace583e93bd96e260164948d400c13a17094f`, rama `main`, árbol limpio. E1 y sus correcciones/aprobación ya estaban incorporadas: no había cambios ajenos sin commit que atribuirse ni mezclar. La revisión efectiva final es ese commit más los archivos indicados en el manifiesto al final. No se hicieron commits.

Fuentes revisadas: informe 0A; contrato 0B v1.1 (MODEL-01–03, TRACE-01/02 base, EVAL-02, TRACE-04); informe E1 original, corrección y aprobación operativa; implementaciones/pruebas E1; contrato PostgreSQL Docker de instancia única. No se encontraron AGENTS.md en el repositorio ni ancestros. La puerta E1 se conserva **APROBADA** según el informe operativo y la evidencia aportada por el usuario; no se repitió el hash operativo del dataset, al conservarse resolver/integridad.

| Dimensión | Estado |
|---|---|
| Registro, configuración, adaptadores e integración local | Implementados |
| Suite aislada consolidada | 138 aprobadas, 2 omitidas (PostgreSQL), 2 advertencias |
| Recuperación de errores/KeyboardInterrupt en fixture legacy adaptado | 2 aprobadas; 2 casos con escritores legacy no ejecutados |
| Integración PostgreSQL E2 | NO VERIFICADA: acceso al socket denegado en esta sesión |
| Puerta E2 | **NO APROBADA**; no se convierte la evidencia crítica pendiente en observación |

## 2. Diseño y cambios comprobados

Rutas relativas al proyecto `malaria_dl_local_project`, salvo indicación contraria.

- `models/registry.py` dentro de `src/malaria_dl`: se conecta el registro existente, reemplazando valores de constructor por `ModelDescriptor`. Declara identidad/aliases, enabled/trainable, versión, adaptador diferido, configuración, contratos, estrategias, optimizadores y preprocesamiento. Rechaza duplicados/aliases ambiguos/descriptores incompletos y solicitudes no ejecutables. No hay fallback de arquitectura.
- `models/optimizers.py`: nombres/defaults validados y única fábrica usada por los compiladores. No se duplican choices de optimizadores en ambos CLIs. Explicita momentum SGD=.9, weight_decay AdamW=.004 y demás opciones; contrasta runtime con `get_config()` y registra los defaults adicionales de Keras.
- `models/adapters.py`: `AdapterResult`, tres adaptadores, validación de firma/sigmoid y `compile_phase`. El adaptador construye sin compilar; el motor compila una vez por fase. Fine-tuning conserva las últimas cuatro capas por defecto, con optimizador nuevo y estado reiniciado. Se rechaza un adaptador que ya devuelve el modelo compilado en base.
- `models/architectures.py`: mismos filtros, cabezas, dropout, L2, congelación y DenseNet training=False. Opciones explícitas para devolver sin compilación y aplicar dropout. Constructores legacy conservan compilación por defecto. BCE pasa de alias a instancia con from_logits=False, label_smoothing=0, axis=-1 y reducción sum_over_batch_size: prueba numérica de equivalencia con la función anterior. No se cambia la loss científica.
- `models/configuration.py` y `configs/models/{custom_cnn,vgg16,densenet121}.json`: esquema versionado; tipos/finitud/rangos y campos desconocidos; parámetros incompatibles/ignorados; defaults → JSON seleccionado → overrides explícitos. No se envía un dict arbitrario como kwargs. Parámetros fuera de capacidades (head/BN distinto, L2 transfer, capas adicionales) se rechazan; no se promete configurabilidad irrestricta.
- `training/cli.py`, `src/train.py` y extracción `data/cli.py`: parseo/inspección sin TensorFlow ni construcción/BD; compatibilidad del entrypoint canónico y del import histórico. TRAIN continúa exigiendo dataset UUID. `--track-db` queda compatible/redundante: todo TRAIN nuevo tiene tracking obligatorio. `--dry-run` no acredita verificación operacional.
- `training/trainer.py`: elimina ramas de arquitectura y defaults paralelos; usa descriptor, adaptador y objeto resuelto. Rechaza discrepancias de opciones comunes con el objeto resuelto. Mantiene guardas E1 y snapshot del dataset. Persistencia estricta antes de cada fit y al finalizar selección; no se completa normalmente sin model_version_id o si falla esa persistencia.
- `run_train_all_models.py`: descubre habilitados entrenables, o respeta subconjunto explícito. Valida toda la matriz antes del preflight/primer hijo. Transmite configuración inline, digest y procedencia; el hijo verifica igualdad de resolución. Conserva UUID/evidencia E1 fijados. Matriz predeterminada **3 × 4 × 1 = 12**, incluida VGG16+SGD. No hay campaign_id/ledger ni promesa de inmutabilidad de campaña entre procesos.
- `persistence/tracking.py`: nombres canónicos del registro y metadatos de modelos entrenables derivados del descriptor. Los históricos y sus alias/rutas no se renombran ni se rellenan retroactivamente.

## 3. Persistencia y semántica

`persistence/model_configuration.py`, `persist_model_configuration`, usa las columnas existentes de `runs` y actualiza únicamente el TRAIN/UUID de dataset indicado. Escribe `execution_parameters.model_configuration_e2`, luego compara una lectura posterior completa. No usa safe_track ni fallback en ese camino; error público sanitizado `MODEL_CONFIGURATION_PERSISTENCE_FAILED`.

Snapshot: requested/resolved, procedencia original y transporte cuando hay lote, versión del esquema/adaptador, modelo canónico, arquitectura efectiva, firma, optimizer.get_config(), loss/compile config, capas por fase, callbacks, augmentation, dataset/snapshot, opciones de ejecución, código efectivo, Python/framework/dependencias, dispositivos y determinismo disponible. Conserva información de base cuando se agrega fine-tuning. El snapshot final incorpora selección, model_version_id y objetivo clínico separado. Los defaults efectivos de BCE y del optimizador se verifican con objetos reales.

Se excluyen configuración E2 y transporte JSON del payload destinado a JSON legacy. Los datos estructurados añadidos se conservan en PostgreSQL, no en archivos de resultados paralelos. Los archivos JSON nuevos versionados son configuración de desarrollo. Se conserva la migración integral de escritores legacy de historia/predicciones para E5–E6: no se afirma que todo TRAIN opere ya sin CSV ni se ejecutó el camino completo que los escribe.

F2 exige beta=2 tanto en CLI como en `CheckpointPolicyConfig`; beta2.5 ahora falla explícitamente. El callback común sigue calculando F2. `selection_semantics` resuelve monitor explícito/política y Early Stopping; se fija y persiste threshold de selección=.5. Se conservan colapso y fallback existentes. `clinical_objective_status` contrasta recall y colapso independientemente de policy_satisfied/completitud técnica; falta de recall es desconocido, no éxito clínico.

Hash/tamaño y vínculo de checkpoint/artefacto/model_version del finalizador existente permanecen; se exige model_version_id antes de terminar normalmente. No se afirma cierre integral de consumidores y selección de versiones E5–E6.

## 4. Matriz contractual

| Requisito | Cambio | Prueba / evidencia real |
|---|---|---|
| MODEL-01 / S04–05 | Registro consumido por CLI, trainer y matriz; capacidad/habilitación | `test_discovery_and_descriptor_errors`: registro sintético añade cuatro combinaciones sin editar consumidores, excluye deshabilitado/no entrenable, prueba TRAIN y construcción/paso/save/load; `test_lazy_cli` comprueba ausencia de import TensorFlow |
| MODEL-02 / S21 | Retorno uniforme y compilación única por fase | `test_real_adapters_step_and_reload`, tres arquitecturas reales weights=None, input32, batch2; cuatro optimizadores por arquitectura, paso base y FT transfer; salida binaria, capas, optimizer y save/load |
| MODEL-03 / S05, S21 | Configuración estricta y precedencia | `test_invalid_config_before_adapter` (12 casos), `test_precedence_requested_resolved_and_tracking`, `test_optimizer_config` (4), `test_matrix_invalid_combination_rejected_before_preflight` |
| TRACE-01 base / S21, S24 | Snapshot completo y lectura estricta antes de fit | `test_persistence_roundtrip_failure_no_files`, `test_persistence_rejects_changed_readback`, `test_persistence_failure_blocks_fit`; PostgreSQL E2 pendiente |
| TRACE-02 base / S12, S24 | Preserva finalizador/resolver, exige identidad; recarga de adaptadores | Suites `test_training_model_version_finalizer.py`, `test_model_version_resolver.py` y round-trip Keras. Alcance consumidor integral continúa E5–E6 |
| EVAL-02 / S19, S27 | Beta2, monitor y objetivo clínico independiente | `test_f2_and_monitor_semantics` (TP1/FN1/FP0 → F2=5/9), `test_beta_rejected_in_cli_and_policy`, `test_clinical_target_independent_of_technical_selection`; suites checkpoint/early_stopping con fallback/colapso |
| TRACE-04 aplicable | Nuevos snapshots en JSONB, sin sidecars/fallback | Pruebas de error/lectura alterada bloquean; inspección de nuevos escritores; cero CSV en temporales E2. Integración real pendiente |
| DATA-01–04 / regresión E1 | UUID obligatorio y evidencia fija conservados | `test_dataset_stage1.py` y resto de regresión E1; fixture adaptada a registro/adaptador sin eliminar guardas |

La prueba sintética no agrega arquitectura productiva: registro temporal restaurado por monkeypatch. Tolerancia de recarga de las tres arquitecturas: `rtol=1e-5`, `atol=1e-6`, entrada y seed sintéticas. No se entrenó con datos operativos ni se buscó mejora clínica.

## 5. Comandos y resultados

Desde `malaria_dl_local_project`:

```sh
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/e2-mpl \
XDG_CACHE_HOME=/private/tmp/e2-cache .venv/bin/python -B -m pytest \
-q -p no:cacheprovider --basetemp=/private/tmp/e2-final2 \
tests/test_model_registry_e2.py tests/test_model_configuration_postgres.py \
tests/test_dataset_stage1.py tests/test_dataset_evidence_postgres.py \
tests/test_governed_dataset_contract.py tests/test_run_evaluate_all_trainings.py \
tests/test_run_explain_all_trainings.py tests/test_train_checkpoint_policy_args.py \
tests/test_max_epochs_config.py tests/test_train_integration.py \
tests/test_evaluation_finalization_integration.py tests/test_checkpoint_policy.py \
tests/test_early_stopping_policy.py tests/test_training_model_version_finalizer.py \
tests/test_model_version_resolver.py tests/test_densenet_model.py
```

**138 passed, 2 skipped, 2 warnings in 23.01s**. Omisiones: E1 PostgreSQL (ya acreditada en E1, no repetida aquí) y E2 PostgreSQL pendiente. Advertencias protobuf ya conocidas; sin GPU soportada. Son pruebas de software, no evidencia clínica.

Se volvió a verificar después de añadir la guarda de consistencia del main: `test_model_registry_e2.py -k persistence_failure_blocks_fit`, **1 passed, 30 deselected**, 2.66s (repetición, no sumar como caso nuevo).

Se adaptó la fixture legacy `test_max_epochs_main_smoke.py` al adaptador y tracking obligatorio, con persistencia/finalizador mockeados para impedir acceso operacional. Se ejecutaron sólo `-k 'failure or interrupt'`: **2 passed, 2 deselected**, 2.75s. Sus otros dos casos ejercitan escritores legacy y no se ejecutaron en E2. No se afirma aprobación de toda la suite del repositorio.

Durante implementación se observaron cinco fallos de fixtures antiguas (listas/builder retirados y beta2.5 previamente aceptado); se actualizaron los puntos de prueba al contrato nuevo y los casos consolidados pasaron. Dos intentos de crear el archivo de test usaron un prefijo de directorio duplicado y no lo crearon; se corrigió la ruta. No se presentan esos intentos como pruebas aprobadas.

Entorno local comprobado: Python3.12.13, TensorFlow2.17.1, Keras3.14.1, NumPy1.26.4, SQLAlchemy2.0.51, psycopg3.3.4. La identidad de entorno se serializó correctamente sin consultar BD.

También: `git diff --check`, Ruff F y parseo AST de módulos cambiados/nuevos; comprobación de CLI sin TensorFlow; serialización de identidad de entorno sin secretos. Conteo de CSV bajo los temporales de pruebas E2: **0**. No se instalaron dependencias ni se ejecutaron migraciones, seeds o servicios.

## 6. Integración PostgreSQL pendiente y aislamiento

Se intentó desde la raíz:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE2_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_model_configuration_postgres.py
```

Salida1, error sanitizado:

```text
permission denied while trying to connect to the docker API at unix:///<usuario>/.docker/run/docker.sock
```

No significa que PostgreSQL esté caído. No se modificaron permisos/socket/servicios ni se conectó otra BD.

La prueba utiliza la instancia Compose autorizada. Crea una tabla TEMP `runs` con los campos usados por el escritor, que oculta `public.runs` sólo en esa sesión; verifica la resolución al schema temporal antes del INSERT. Todos los UUID/payloads son sintéticos. Usa transacción externa y savepoints para commits internos; prueba round-trip y rechazo de identidad incorrecta sin perder la transacción. Revierte siempre y comprueba en conexión posterior READ ONLY que no quedó la tabla temporal ni apareció el UUID sintético en `public.runs`. Acumula errores de limpieza sin sustituir el original, con diagnóstico sanitizado.

**El aislamiento fue revisado en código; inserción/igualdad/rollback PostgreSQL no se ejecutaron en esta sesión.** El comando anterior queda listo para la terminal autorizada con los archivos actualizados visibles. No requiere cambios al esquema operativo. Incluso al pasar, esta prueba verifica el repositorio contra campos tipados aislados, no todos los constraints/permisos de UPDATE de `public.runs` ni durabilidad de un commit entre sesiones. No se crea un TRAIN científico ficticio para acreditar persistencia.

## 7. Compatibilidad y límites E3–E9

VGG16 **actual E2**: auto → rescale_0_1, igual al comportamiento histórico; vgg16_imagenet sigue siendo opción explícita. **Objetivo E3**: exigir contrato ImageNet en nuevos TRAIN, sin doble transformación y sin reinterpretar checkpoints históricos. E2 sólo declara/prepara ese contrato. DenseNet mantiene normalización interna y training=False; no se altera la selección científica de checkpoints.

Selección de Producción Etapa 2 permanece manual. No hay cambios en `malaria_dataset_split_project`, dataset/split, imágenes, checkpoints históricos, esquema/migraciones, frontend/backend o publicaciones. Las modificaciones están acotadas al ML, fixtures, configuración y documentación indicadas. Informe 0A, contrato 0B e informes E1 se conservan.

Pendiente: integración E2; E3 preprocessing; E4 entidades/configuración de campañas; E5 ejecución durable, cronología integral de LR/resultados y migración TRAIN sin CSV; E6 consumidores/evaluación/EXPLAIN y sus resultados; E7 comparación/protocolo; E8 extensiones; E9 regresión/campaña autorizada. No se inicia E3 ni campaña científica. No se declara equivalencia bit a bit entre hardware ni durabilidad de un commit a partir de un rollback.

Guía: [Cómo agregar y habilitar un modelo](../../malaria_dl_local_project/docs/model_registry_e2.md).

## 8. Manifiesto de revisión efectiva

Hashes SHA-256 de archivos modificados/nuevos del proyecto ML al cierre; el commit base está indicado arriba. Este manifiesto identifica el árbol efectivo sin crear un commit ni incluir artefactos operativos.

| Archivo | SHA-256 |
|---|---|
| `malaria_dl_local_project/README.md` | `3de8edeedf3c63c594e7ed6a4e19ff851a766b82680485e30e5cd75735c02cc0` |
| `malaria_dl_local_project/configs/models/custom_cnn.json` | `b219adae19aa2d54cc43c2bc2fcfa0cd92d8cc622d4e3df5e7d1ced58b1c07df` |
| `malaria_dl_local_project/configs/models/densenet121.json` | `52d7b3d19d8b5b548d43ac71a86a88d99e500461ea76cc06af08ccc25ef522b0` |
| `malaria_dl_local_project/configs/models/vgg16.json` | `489289f0f873451477b99f01dbaa18a3de347518244e3654106d0f66e9edf825` |
| `malaria_dl_local_project/docs/model_registry_e2.md` | `c07c8a90b7c0b5ba13b03eb64759153269113bd4fd9d6950364fd017bf0d92b7` |
| `malaria_dl_local_project/run_train_all_models.py` | `6d0d551b3a088d1add39110e0d81b52037e0a137fbe27b86be1dec5f1ff98ef5` |
| `malaria_dl_local_project/src/malaria_dl/data/cli.py` | `ca477a6a1d53f09eb76fd3a455ff157aae4656aabea3bee4a4f83c2d0f6cd042` |
| `malaria_dl_local_project/src/malaria_dl/data/loaders.py` | `05c2fecfa910cbdaaaa13173b60ad91c51fa155df22c8540eae0f3c4acb3231a` |
| `malaria_dl_local_project/src/malaria_dl/models/adapters.py` | `f71e3a69bdf896f28e76824f68a202ab8f1991f45219309405fbfb2d67faecfa` |
| `malaria_dl_local_project/src/malaria_dl/models/architectures.py` | `ef5fb77e023079597fc86c0fc1725a2366ab212f2148fb5c9e8deb7ec9968662` |
| `malaria_dl_local_project/src/malaria_dl/models/configuration.py` | `0f48f549ccd18fe808b32f8b45fa7ae5649923a47d6f58ae1c957eeb9cc7f337` |
| `malaria_dl_local_project/src/malaria_dl/models/optimizers.py` | `ed93e8aa4ee4bd155acbc64a82257b20c581e147ba285591ef63ac6f5ab1012a` |
| `malaria_dl_local_project/src/malaria_dl/models/registry.py` | `ef379aaa9df74cf7a558b559aa078d87507a7b7c9b6761c38ea1d4a2c2d571e2` |
| `malaria_dl_local_project/src/malaria_dl/persistence/model_configuration.py` | `ae789ab36ec5821915f70dbd7b399380a2f284621abc70858ef2a77b3a41f088` |
| `malaria_dl_local_project/src/malaria_dl/persistence/tracking.py` | `4854946e7e1ec0316a5594469f469b1c27b47e2ea743ec61afd218576ecff80d` |
| `malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py` | `149eccd7aa53bc2cd0f6c856b76a10a64fc0ca923a075b6aa6086c86b89efa0d` |
| `malaria_dl_local_project/src/malaria_dl/training/cli.py` | `0edf4b87894af15bf00411d0c3e66abba171fc982b53a558a18a34d7040a6418` |
| `malaria_dl_local_project/src/malaria_dl/training/cli_constants.py` | `401c998df8d1f5b5cbc328cc72ace2ebd11445d3a3aab5d8a38b6308f05a5edc` |
| `malaria_dl_local_project/src/malaria_dl/training/trainer.py` | `65bbd854f77a65f01df9c6c39f8c13bb675371d2923f7faabf8244e947fc48f1` |
| `malaria_dl_local_project/src/train.py` | `c494eed68c5c9546863a371d325754ebba9d26ee6bee27393ef3bcaa903f5115` |
| `malaria_dl_local_project/tests/test_dataset_stage1.py` | `12a1af386d077fcf40dc1ffe9940835efca434fac0307c90ee32d77891649633` |
| `malaria_dl_local_project/tests/test_max_epochs_main_smoke.py` | `099f1c203975afb60b7267f053642cbb7fafa4bfe69c96ce27ed5badbf01d9f2` |
| `malaria_dl_local_project/tests/test_model_configuration_postgres.py` | `30ffc26c67206a426e89979b76c0cf65cf89e1c95334395024bae79e29aeca69` |
| `malaria_dl_local_project/tests/test_model_registry_e2.py` | `903c28d4a9eaaf85cfdad267d40642492cf46c3e2f491e13f7bc5e7f8fa4fcb9` |
| `malaria_dl_local_project/tests/test_train_checkpoint_policy_args.py` | `f7d20ceaccfffb249aa4d432260a9dfe927e5723276d5603514ce3748488d8ec` |
