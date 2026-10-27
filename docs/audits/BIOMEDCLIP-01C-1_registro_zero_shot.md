# BIOMEDCLIP-01C-1 — Contratos científicos y registro Zero-shot

Fecha: 2026-10-26, America/Santiago (cierre de evidencia: 2026-10-27 UTC).
Referencia Git: `41b6f572a132b0499c6883298f8f5a2483cb2232`, rama `main`.
Estado: **implementado y validado en bases aisladas del esquema actual; no desplegado en producción**.

## 1. Resumen de implementación

Se implementó `python -m src.register_pretrained`, independiente de TRAIN. Registra el original BiomedCLIP y sus cuatro componentes auxiliares, con configuración científica inmutable, sesión verificada sin épocas y linaje `runs → artifacts → model_versions`.

Se leyeron completos antes de editar el [contrato arquitectónico](../architecture/capstone_scientific_artifacts_and_persistence.md), [01A](BIOMEDCLIP-01A_auditoria_integracion.md) y [01B](BIOMEDCLIP-01B_validacion_gpu_y_frameworks.md), especialmente §12 de 01B. Se contrastaron con código y un `pg_dump --schema-only` actual. No se consultaron revisiones Alembic ni se añadieron verificaciones de versión de esquema.

Estado inicial: `main`, sin cambios rastreados; ya estaban sin seguimiento el informe 01B, `docs/audits/evidence/` y `scripts/experiments/`. Se conservaron. No hubo commits, merges, instalación en el venv productivo, reinicio de servicios ni modificaciones de `.env`.

Resultados:

- **42 pruebas** de registro/SQL/archivos/ownership/concurrencia aprobadas; una prueba adicional del comando TRAIN con selección mixta también aprobada.
- **303 pruebas de regresión** aprobadas, incluidas operaciones convencionales, verificadores, linaje y model versions.
- **442 pruebas frontend** aprobadas; compilación TypeScript/Vite aprobada.
- Registro real con rol **no superusuario**, sin configuraciones de optimización, registros de aprendizaje ni assessments Zero-shot.
- Esquema productivo idéntico al respaldo; mismas cantidades y huellas de filas en las 12 tablas auditadas.

No se implementaron ni ejecutaron EVALUATE, TEST, EXPLAIN o REPRESENT BiomedCLIP. No se registraron Linear ni Fine-tuning.

## 2. Contratos científicos definitivos

El discriminante vive en `runs.execution_parameters.scientific_origin`, junto con `pretrained_configuration` y `configuration_hash`. No se añadió columna ni tabla. La configuración completa se conserva también como identidad inmutable de la sesión; las referencias de artefactos y versión vinculan su hash.

```json
{
  "schema": "pretrained_origin_v1",
  "kind": "pretrained_external",
  "mode": "zero_shot",
  "training_performed": false,
  "architecture": "biomedclip_zero_shot",
  "model_repository": "microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224",
  "revision": "9f341de24bfb00180f1b847274256e9b65a3a32e"
}
```

`pretrained_configuration_v1` contiene exactamente origen, protocolo `biomedclip_zero_shot_inference_v1`, snapshot de dataset objetivo, framework y versiones. Python y PostgreSQL validan el protocolo completo, no una etiqueta permisiva. El modelo SQL debe ser Zero-shot, `metadata.trainable=false`, preentrenado y del repositorio aprobado. Un modelo convencional no puede adoptar esta rama.

El protocolo fija:

- ViT-B/16, proyección visual lineal, texto BiomedBERT, proyección MLP, **`cls_last_hidden_state_pooler`**, contexto 256.
- Tokenizer/revisión/vocabulario originales; limpieza whitespace, lowercase, padding máximo, truncación y conservación del separador.
- RGB, resize del lado corto a 224, bicubic con antialias, center crop 224, tensor float32 NCHW dividido por 255 y normalización original.
- Media `[0.48145466,0.4578275,0.40821073]`; desviación `[0.26862954,0.26130258,0.27577711]`.
- Embeddings proyectados multimodales de 512 dimensiones, normalizados L2.
- Orden `uninfected=0`, `parasitized=1`, positiva 1. Un prompt por clase, sin ensemble.
- `softmax(exp(logit_scale) * cosine(image,text))[1]`; escala del original `85.2322769165039`.
- Score relativo a los dos prompts, **no probabilidad clínica calibrada**. Umbral protocolizado 0,5, regla `>=`, calibración inexistente (`null`), fijado antes de TEST.

Prompts exactos:

```text
0: a microscopy image of an uninfected red blood cell.
1: a microscopy image of a red blood cell infected with malaria parasites.
```

La escala procede de la evidencia de carga del checkpoint exacto en 01B; aquí se revalida su identidad binaria, sin hacer inferencia. Configuración completa recuperada: [registered_origin.json](evidence/biomedclip_01c1/registered_origin.json).

El snapshot corresponde al **dataset objetivo**, no a datos empleados para preentrenar. Se reutiliza el resolvedor gobernado con `required_splits=()`: comprueba freeze, materialización, checks, asignaciones, fingerprints y conteos sin abrir imágenes, incluido TEST.

## 3. Componentes modificados

| Componente | Cambio |
|---|---|
| `src/malaria_dl/pretrained/contracts.py` | Origen, protocolo cerrado, componentes y `PretrainedCompletionContractV1` |
| `pretrained/repository.py` | Persistencia transaccional y recuperación verificable sobre las tablas existentes |
| `pretrained/service.py` | Resolución gobernada, hashes reales, exclusión concurrente e idempotencia |
| `pretrained/training.py` | Omisión operativa de descriptores no entrenables, sin registro |
| `src/register_pretrained.py` | Comando explícito; salida JSON y errores sanitizados |
| `models/registry.py`, `configs/models/biomedclip_zero_shot.json` | Descriptor no entrenable, sin adapter/optimizer/estrategias ficticios |
| `campaigns/configuration.py`, `campaigns/contracts.py` | Capacidad en catálogo, presets sólo entrenables y rechazo de selección Zero-shot |
| `execution/selection.py`, `operations.py`, `train.py`; `training/cli.py`, `trainer.py` | Identificación del modelo antes de exigir configuración de optimización; omisión y continuación |
| `execution/artifacts.py` | Error explícito `PRETRAINED_ASSESSMENT_NOT_IMPLEMENTED` ante el verificador convencional |
| `frontend/src/pages/CampaignConfiguration.tsx`, `types/campaign.ts` | Checkbox deshabilitado y motivo exacto |
| `requirements-biomedclip-registration.txt` | Dependencias principales fijadas de la pila validada; no se instalaron en producción |
| `scripts/sql/biomedclip_01c1.sql` | SQL explícito del catálogo y los contratos actuales |
| `tests/test_biomedclip_pretrained.py` | Pruebas nuevas, incluidas escrituras en clon actual y binarios reales |

Las rutas Python de la tabla son relativas a `malaria_dl_local_project/`. Se reutilizan `ExecutionRepository`, `CampaignRepository`, `execute`, `canonical`, `digest`, `file_identity`, `local_scientific_path`, `GlobalGate` y el resolvedor del dataset. No se crearon endpoints ni otro almacén científico.

## 4. SQL y restricciones adaptadas

[SQL de instalación](../../scripts/sql/biomedclip_01c1.sql), transaccional `BEGIN/COMMIT`, probado mediante `psql -v ON_ERROR_STOP=1`. Es una instalación explícita única contra el esquema actual; no incluye detección de versiones ni fallback.

- `v2_run_configuration_required`: TRAIN convencional conserva su exigencia de `run_configurations`. Zero-shot exige al cierre de transacción configuración válida, sesión `verified`, completion íntegro y RUN `completed`. Un RUN incompleto no puede quedar confirmado.
- `train_session_guard`: conserva identidad, propietario, fencing y transiciones. Añade la rama de registro que exige `pretrained_completion_valid`; la rama convencional sigue exigiendo épocas, artefacto y hashes de records.
- Validadores de origen/configuración/completion vinculan catálogo, dataset/materialización, fingerprints/checks/conteos, protocolo exacto, hashes, sesión, cinco artefactos y versión.
- `pretrained_run_guard`: impide suplantar/eliminar/modificar origen y configuración. Rechaza campos de optimización o selección en Zero-shot.
- Índice único `pretrained_scientific_identity` sobre el hash de configuración de los orígenes: respalda la idempotencia aun frente a escritores que no tomen el lock de aplicación.
- Guards específicos conservan identidad de catálogo, artefactos, model versions y metadata. Verifican ownership y bloquean aprendizaje ficticio en `train_execution_records`, `training_history` y `run_configurations`.
- La inserción de sesiones exige propietario y estado inicial `active`. El guard de campañas impide configuración Zero-shot; el contrato de configuraciones vigente también conserva su dominio entrenable.

No se eliminaron PK, FK, UNIQUE, CHECK, NOT NULL ni triggers. Se conserva la FK compuesta de versión a `(checkpoint_artifact_id,training_run_id)`. No se desactivaron triggers ni se cambió `session_replication_role`.

Las dos definiciones sustituidas se conservaron para revisión en [original_guards.sql](../../scripts/sql/biomedclip_01c1_original_guards.sql). No es un rollback automático: restaurarlas después de registrar orígenes dejaría consumidores incompatibles. Recuperación segura en §13.

## 5. Diseño de la operación de registro

Secuencia real:

1. Resolver el catálogo y dataset gobernado; construir configuración y leer versiones efectivas.
2. Rechazar archivos ausentes, links o identidades distintas; leer SHA-256/tamaño de cada componente original.
3. Tomar advisory lock de identidad científica. Si existe, recuperar y verificar relaciones y **bytes gobernados** antes de informar reutilización.
4. Para una identidad nueva, adquirir el `GlobalGate` vigente, sin relajar su bloqueo ni sus permisos.
5. En una transacción: revalidar dataset, crear RUN/sesión, copiar componentes a un directorio UUID exclusivo, registrar artefactos y model version.
6. Verificar archivos copiados; completar sesión, verificarla y completar RUN; forzar constraints diferidos antes de commit.
7. Recuperar y volver a verificar el registro; devolver identificadores, configuración y estado.

Raíz definitiva: `malaria_dl_local_project/outputs/train_runs/<run_id>/`. Se copian bytes con creación exclusiva, `fsync` y permisos de archivo `0444`; no son symlinks/hardlinks al cache. La recuperación por repositorio no necesita el cache original.

Comando ejecutado desde `malaria_dl_local_project` en la base aislada:

```sh
export BIOMEDCLIP_TEST_DATABASE_URL='postgresql+psycopg://biomedclip_test_runtime@127.0.0.1:55439/biomedclip_01c1_runtime'
/Users/julio/.cache/capstone-biomedclip-01b/venv/bin/python -m src.register_pretrained \
  --database-url-env BIOMEDCLIP_TEST_DATABASE_URL \
  --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
  --biomedclip-directory /Users/julio/.cache/capstone-biomedclip-01b/original/biomedclip/9f341de24bfb00180f1b847274256e9b65a3a32e \
  --text-directory /Users/julio/.cache/capstone-biomedclip-01b/original/text/d673b8835373c6fa116d6d8006b33d48734e305d
```

Sin `--database-url-env`, utiliza el `get_engine` configurado de la aplicación. El parámetro opcional identifica una variable, no expone credenciales en argumentos. No se redirige silenciosamente a producción mediante bootstrap de TRAIN.

## 6. Identidad y hashes

Repositorio principal y revisión: `microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224` / `9f341de24bfb00180f1b847274256e9b65a3a32e`.
Texto: `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract` / `d673b8835373c6fa116d6d8006b33d48734e305d`.

| Componente | Bytes | SHA-256 |
|---|---:|---|
| `open_clip_pytorch_model.bin` | 783705670 | `52cc993c5c5ff962bd0c60931874bc001e7e9b41666a385530f4a036294576be` |
| `open_clip_config.json` | 707 | `9a41f334a8c444678772c0ebb9ab854c97ab350bced3a17b803e258d39c23dc0` |
| `text/config.json` | 385 | `56bab767c02bc792897638feb8addc06d483d9c73769a5f554bbabea1f5507a1` |
| `text/tokenizer_config.json` | 28 | `53b6f42b8b8daddbdc6d3532c324187a92b46c1602bd6e8d4ad5a413b4fc90e1` |
| `text/vocab.txt` | 225062 | `7b36651908a88bc38bda41b728b2a598191e0d3b553cbacf7b1e5f026d5b5b9f` |

El hash de configuración usa la serialización canónica existente: claves ordenadas, listas ordenadas, floats integrales normalizados. SQL reutiliza `assessment_canonical`. La configuración incluye el snapshot de localización registrado del dataset: cambiar ese snapshot o las versiones de framework cambia la identidad. No existe resolución por `latest`/`main`.

Versiones efectivas: torch 2.14.1, torchvision 0.29.1, open_clip_torch 3.3.0, transformers 4.57.6, timm 1.0.30, tokenizers 0.22.2 y numpy 1.26.4. Python y plataforma quedan en environment de sesión. El lock completo de 01B permanece como referencia de entorno.

## 7. Contrato de completion

`PretrainedCompletionContractV1` contiene exclusivamente:

```text
schema, run_id, owner, model_id, dataset_version_id,
artifact_id, model_version_id, configuration_hash, components_hash
```

La verificación vincula estos campos al RUN, catálogo, configuración, snapshot, sesión, checkpoint y todos los componentes. `verification` contiene `status=verified`, el completion exacto y las identidades de componentes. La versión queda `candidate/resolved`, sin publicar Stage 2.

No se reutiliza `TrainingCompletionContractV1`. No existen época seleccionada, optimizer, loss, calibration VAL, métricas TRAIN o history ficticios. La columna heredada `runs.completed_epochs` conserva su default obligatorio `0`: es ausencia de épocas, no evidencia de aprendizaje. Los demás campos opcionales de aprendizaje quedan NULL; las tablas de aprendizaje/configuración optimizadora no tienen filas para este RUN.

SQL verifica coherencia relacional y declaraciones de identidad; la lectura de bytes del host corresponde a Python. Ningún constraint PostgreSQL afirma que por sí solo pueda leer archivos de macOS. La recuperación revalida físicamente el origen y falla ante pérdida o mutación.

## 8. Comportamiento del catálogo

`models.metadata` representa `family=biomedclip`, `trainable=false`, `registration=pretrained_origin_v1`. El descriptor Python es independiente de las tres implementaciones existentes.

El catálogo HTTP existente conserva el modelo visible, con parámetros/optimizadores vacíos, `trainable=false` y `disabled_reason="No requiere entrenamiento local"`. El checkbox tiene `disabled` y no aparece marcado por una configuración manipulada. Los presets y el producto cartesiano predeterminado incluyen sólo entrenables. La validación backend rechaza una selección explícita Zero-shot antes de crear miembros.

La compilación y las pruebas frontend fueron ejecutadas; no se hizo una sesión de prueba visual en navegador ni se desplegó la UI. El catálogo productivo sigue teniendo tres modelos porque la inserción SQL no está autorizada allí.

## 9. Comportamiento de `src.train`

La selección devuelve el nombre SQL del modelo. Antes de exigir optimizer/recipe, `training_plan` omite los no entrenables y continúa el resto. Emite JSON operativo:

```json
{"model":"biomedclip_zero_shot","state":"omitted","reason":"No requiere entrenamiento local"}
```

Sólo Zero-shot produce un plan vacío y retorno exitoso sin RUN/sesión nuevos. Se verificó el comando `operations.main` sobre el RUN real de la base aislada, comparando conteos antes/después. Se probó una selección mixta en el adaptador de selección y en el comando, comprobando que se llama al ejecutor sólo para Custom CNN y nunca al registro.

El launcher histórico `training.cli`, `trainer.main` y `execution.train.standalone` también omiten antes de ejecutar TRAIN. Las campañas nuevas no pueden incluir Zero-shot: no se modifica una matriz congelada para convertir el registro en miembro entrenable. Las pruebas mixtas usan selección controlada; no se inventó una campaña SQL inválida ni se ejecutó entrenamiento BiomedCLIP.

## 10. Pruebas positivas

Implementación: [test_biomedclip_pretrained.py](../../malaria_dl_local_project/tests/test_biomedclip_pretrained.py). Evidencia: [42 casos](evidence/biomedclip_01c1/registration_tests.txt) y [comando mixto adicional](evidence/biomedclip_01c1/train_mixed_entry_test.txt).

| Requisito | Prueba / resultado |
|---|---|
| 1. Aparece en catálogo | `test_catalog_visible_disabled_and_presets`; aprobado |
| 2. No seleccionable para TRAIN | Flags, preset y rechazo de selección manipulada; aprobado |
| 3. TRAIN omite | `test_train_skips_and_continues_without_registration`, entrada real y argumentos legacy; aprobado |
| 4. Continúa entrenables | Plan y `test_train_main_continues_trainable_sources`; aprobado con ejecutor controlado |
| 5. Sólo Zero-shot no crea RUN | `test_train_entry_only_zero_leaves_database_unchanged`; aprobado en SQL real |
| 6. RUN training | Registro CLI real y consulta SQL; aprobado |
| 7. Origen conservado | Igualdad de configuración/origen recuperados; aprobado |
| 8. Artefacto propietario | Cinco filas, checkpoint vinculado al RUN; aprobado |
| 9. model_version correcta | FK/modelo/RUN/checkpoint/estado comprobados; aprobado |
| 10. verified sin épocas | Estado y contrato válidos, cero records/history; aprobado |
| 11. Checkpoint recuperable | Hash/tamaño de todos los archivos gobernados; aprobado |
| 12. Configuración reconstruible | Recuperación íntegra y equivalencia Python/SQL/config original; aprobado |
| 13. Sin aprendizaje ficticio | Cero run_configurations/history/records/assessments; aprobado |
| 14. Idempotencia | Segunda invocación devuelve mismo RUN con `reused=true`; aprobado |

## 11. Pruebas negativas

| Requisito | Resultado observado |
|---|---|
| 1. Entrenable simula origen externo | `PRETRAINED_CONFIGURATION_INVALID` |
| 2. Completion TRAIN convencional | Rechazado por parser y transición SQL |
| 3. Checkpoint ausente | Rechazo físico y CLI con exit 2, sin nuevas filas |
| 4. Checkpoint alterado | Rechazo por identidad de bytes y sin éxito parcial |
| 5. Hash incorrecto | Configuración rechazada en Python y SQL |
| 6. Tokenizer incorrecto | Vocabulario alterado en copia independiente; rechazo físico/CLI |
| 7. Revisión mutable | `main` rechazado, en origen y tokenizer |
| 8. Prompts incompletos | Rechazo en Python y SQL |
| 9. Clase positiva incoherente | Rechazo en Python y SQL |
| 10. Dataset inválido | `DATASET_VERSION_NOT_FOUND`, sin registro |
| 11. Configuración incompleta | Rechazo del contrato y SQL |
| 12. Artifact de otro RUN | Rechazo de inserción/reescritura con propietario distinto |
| 13. Model version de otro modelo | `PRETRAINED_VERSION_BINDING_INVALID` o guard inmutable |
| 14. verified sin evidencia | Rechazo por transición/contrato; propietario incorrecto también rechazado |
| 15. Error SQL durante registro | Fallo inyectado al crear model_version; rollback de RUN, sesión y cinco artefactos |
| 16. Modificación del origen verified | Rechazo de origen/metadata/modelo/artifact y eliminación de evidencias |
| 17. Doble registro concurrente | Dos procesos, una creación y una reutilización, mismo RUN y una sola identidad SQL |

Además se probaron umbral/dimensión no aprobados, inserción de aprendizaje ficticio, sesión creada con otro owner, commit incompleto y límites del verificador de assessment. Todos los casos finales ejecutados aprobaron.

Incidencias de desarrollo: el primer intento de concurrencia eligió una versión de dataset que no cumplía el resolvedor gobernado y fue correctamente rechazado; se corrigió el escenario usando el dataset gobernado en otra base vacía de orígenes. Se preservó el error de dominio al traducir `GovernedDatasetError`. La revisión final corrigió el nombre exacto del pooling textual y añadió comparación explícita con el archivo original. Las bases preliminares no son evidencia certificada del contrato final.

## 12. Pruebas de regresión

[Resultado final](evidence/biomedclip_01c1/regression_tests.txt): **303 passed**, 5 warnings de dependencias; 95,76 s. Suites existentes:

```text
test_model_registry_e2.py                 test_campaign_configuration_swv22.py
test_campaigns_e4.py                      test_campaign_executor_e5.py
test_exec1.py                             test_training_completion.py
test_assessment_e6.py                     test_model_governance_repository.py
test_model_governance_entities.py         test_checkpoint_lineage_resolution.py
test_evaluation_training_lineage_service.py
test_training_model_version_finalizer.py
```

Incluyen pasos y recarga de los tres adaptadores convencionales, configuración/campañas, verificación de artefactos, completion, selección CLI, EVALUATE/TEST, XAI convencional, model versions y linaje. Las pruebas SQL nuevas verifican además que TRAIN convencional sigue rechazando ausencia de `run_configurations` y de épocas, y acepta evidencia de época coherente en una transacción sintética que se revierte.

[Primera regresión](evidence/biomedclip_01c1/regression_initial.txt): 299 passed / 4 failed. No se ocultó este resultado. Cuatro aserciones asumían catálogo exclusivamente entrenable: cantidad fija de modelos, resolvedor ejecutable para cada fila y parámetros de optimización para todos. Se actualizaron **dos archivos de pruebas existentes** para verificar descubrimiento SQL y capacidad explícita, afirmar ausencia de parámetros Zero-shot y conservar las aserciones de los tres entrenables. No se eliminaron tests ni se cambiaron verificadores para permitir entrenamiento falso.

La ruta de pruebas [sitecustomize.py](../../scripts/validation/biomedclip_01c1_test_environment/sitecustomize.py) redirige únicamente la conexión de tests y sus subprocess a la base aislada explícita. No filtra catálogo, no modifica SQL ni mocks de comportamiento; no se usa en comandos productivos.

Frontend: [442 passed](evidence/biomedclip_01c1/frontend_tests.txt); [build aprobado](evidence/biomedclip_01c1/frontend_build.txt), con aviso de bundle grande. No se alteró el bundle para este alcance. No se ejecutó la totalidad de todas las suites del monorepo ni campañas largas.

## 13. Transacciones, rollback, respaldo y reproducción

Respaldo previo fuera del repositorio:

```text
/Users/julio/.cache/capstone-biomedclip-01c1/current.dump
/Users/julio/.cache/capstone-biomedclip-01c1/schema_before.sql
/Users/julio/.cache/capstone-biomedclip-01c1/runtime_grants.sql
```

Se produjo `pg_dump` del esquema/datos actuales en lectura; se restauró en **otro contenedor** PostgreSQL, `capstone_biomedclip_01c1_db`, publicado sólo en `127.0.0.1:55439`. No se creó una base dentro del servidor productivo. El dump omite propietarios/ACL; para probar permisos se copiaron explícitamente los grants de tablas/secuencias de `capstone_v2_runtime` a `biomedclip_test_runtime`, rol aislado `NOSUPERUSER NOCREATEDB NOCREATEROLE`.

Bases finales: `biomedclip_01c1_verified` (suite), `biomedclip_01c1_runtime` (creación concurrente y recuperación con rol no privilegiado). Se conservaron las bases de ensayo preliminares, sin borrar datos. No se deben usar esas primeras pruebas como orígenes productivos.

Reproducción desde la raíz, creando nombres nuevos y sin sobrescribir una base existente:

```sh
# Respaldo de lectura actual, o reutilizar el respaldo conservado de esta prueba.
docker exec capstone_db sh -c 'PGOPTIONS="-c default_transaction_read_only=on" pg_dump --format=custom --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > /ruta/segura/current.dump

# En el contenedor aislado ya existente; nunca en capstone_db.
docker exec capstone_biomedclip_01c1_db psql -X -U postgres -d postgres -v ON_ERROR_STOP=1 \
  -c 'CREATE DATABASE biomedclip_01c1_replay' \
  -c 'CREATE DATABASE biomedclip_01c1_replay_race'
for target in biomedclip_01c1_replay biomedclip_01c1_replay_race; do
  docker exec -i capstone_biomedclip_01c1_db pg_restore -U postgres -d "$target" \
    --no-owner --no-privileges --exit-on-error < /ruta/segura/current.dump
  docker exec -i capstone_biomedclip_01c1_db psql -X -U postgres -d "$target" \
    -v ON_ERROR_STOP=1 < scripts/sql/biomedclip_01c1.sql
done
```

Desde `malaria_dl_local_project`, con el Python del entorno validado de 01B:

```sh
export BIOMEDCLIP_TEST_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:55439/biomedclip_01c1_replay'
export BIOMEDCLIP_CONCURRENT_DATABASE_URL='postgresql+psycopg://postgres@127.0.0.1:55439/biomedclip_01c1_replay_race'
/Users/julio/.cache/capstone-biomedclip-01b/venv/bin/python -m pytest tests/test_biomedclip_pretrained.py -q

# Para las suites existentes enumeradas en §12:
export PYTHONPATH=.:../scripts/validation/biomedclip_01c1_test_environment
/Users/julio/.cache/capstone-biomedclip-01b/venv/bin/python -m pytest \
  tests/test_model_registry_e2.py tests/test_campaign_configuration_swv22.py \
  tests/test_campaigns_e4.py tests/test_campaign_executor_e5.py tests/test_exec1.py \
  tests/test_training_completion.py tests/test_assessment_e6.py \
  tests/test_model_governance_repository.py tests/test_model_governance_entities.py \
  tests/test_checkpoint_lineage_resolution.py tests/test_evaluation_training_lineage_service.py \
  tests/test_training_model_version_finalizer.py -q
```

La prueba de concurrencia exige que su base todavía no contenga un origen Zero-shot; usa nombres nuevos en cada reproducción completa. Los assets pueden localizarse mediante `BIOMEDCLIP_ORIGINAL_ROOT`. La prueba de corrupción utiliza `cp -cR` para una copia independiente APFS: su reproducción exacta está dirigida a este host macOS.

Rollback comprobado: el fallo SQL después de crear los artefactos elimina **todas las nuevas filas científicas** mediante rollback. Las pruebas de constraints usan transacciones/savepoints y no alteran históricos. La transacción PostgreSQL no convierte filesystem y BD en una transacción distribuida: un fallo puede dejar una carpeta UUID nueva **sin referencias SQL**, nunca un RUN presentado como verified. Se conservaron esas carpetas de ensayo; no se borraron automáticamente archivos científicos.

Recuperación de una aplicación futura: si el SQL falla antes de COMMIT, revertir la transacción. Si ya hay orígenes registrados, no restaurar sólo los guards antiguos ni borrar registros: restaurar el respaldo en una **base sustituta**, conservar los binarios y verificar referencias antes de un cambio de conexión autorizado. Para un origen con archivo ausente/mutado, reportar el error; no reparar sobreescribiendo su histórico. El respaldo SQL debe acompañarse de copia de las raíces científicas referenciadas.

## 14. Estado real de PostgreSQL

[Consulta final con rol runtime](evidence/biomedclip_01c1/registration_sql_evidence.json):

| Identidad | Valor |
|---|---|
| Base | `biomedclip_01c1_runtime` |
| Rol / superusuario | `biomedclip_test_runtime` / `false` |
| RUN | `310bfe08-0a27-4cf7-a00c-4404f7284d75` |
| Checkpoint artifact | `9170d6e0-832a-46e6-894e-aa3c8936cb0d` |
| Model version | `4e273552-47c7-4b94-b3fa-4a709618f028` |
| Estado | RUN `training/completed`, sesión `verified`, origen/configuración/completion válidos |
| Artefactos | 5 |
| Records, history, optimizer configs, assessments del origen | 0, 0, 0, 0 |

La [recuperación CLI](evidence/biomedclip_01c1/registered_origin.json) devuelve las mismas identidades y `reused=true`, tras volver a verificar bytes.

**Producción:** no se ejecutó DDL, no se insertó el modelo y no se creó ningún RUN desde esta tarea. [Esquema comparado](evidence/biomedclip_01c1/schema_comparison.json): igualdad exacta normalizando únicamente el token aleatorio `\restrict/\unrestrict` de pg_dump. SHA-256 normalizado antes/después: `0af8d7d653f3f68b3233620d6a30b1965bfae561b3a78b2da6fecf5417418456`.

[Snapshot del respaldo](evidence/biomedclip_01c1/database_backup_snapshot.json) y [fuente al cierre](evidence/biomedclip_01c1/database_source_after.json): mismas cantidades y huellas MD5 agregadas de filas en models, runs, artifacts, model_versions, run_configurations, sesiones, records, history y las cuatro tablas assessment auditadas. Producción mantiene 3 modelos, 23 RUN, 23 sesiones, 22 artifacts y 1 model_version. Son controles de esas tablas, no una certificación exhaustiva de toda la base o de todos los binarios históricos. Script de lectura: [snapshot.py](../../scripts/validation/biomedclip_01c1_snapshot.py).

## 15. Riesgos y pendientes

- Despliegue/DDL/catálogo/registro productivo **pendientes de autorización específica**, conforme a §12 de la solicitud. El código y SQL están preparados, no aplicados allí.
- Las pruebas certifican registro y reconstrucción de configuración/identidad, no desempeño clínico, calibración ni nuevo forward del modelo. Inferencia real CPU/MPS sigue respaldada por 01B, sin ampliarla aquí.
- La carpeta científica no es almacenamiento WORM: los permisos evitan escrituras accidentales; toda recuperación vuelve a verificar bytes. Un administrador del host o BD sigue teniendo capacidades administrativas.
- No hay rollback distribuido filesystem/SQL. Pueden quedar binarios huérfanos de fallos de registro; no cuentan como evidencia científica y no se sobrescriben/reutilizan por nombre.
- La identidad incluye el snapshot de raíz registrado del dataset y las versiones efectivas: cambiar esos datos genera otra identidad, aunque el checkpoint sea el mismo. La reutilización de hash de checkpoint queda justificada en model_versions.
- El contrato actual de versión Zero-shot es inmutable y queda candidate; publicación, reportes específicos y cambios de estado posteriores requieren su contrato correspondiente, fuera de esta etapa.
- El entorno productivo no tiene todavía toda la pila OpenCLIP; no se actualizó automáticamente. La prueba utilizó el entorno aislado validado en 01B.
- Las raíces de ensayo nuevas y el contenedor aislado se conservaron para revisión; no son un despliegue ni sustituyen los backups productivos.

## 16. Criterios de entrada a 01C-2

01C-1 queda **técnicamente completada en el entorno de pruebas**, con las limitaciones explícitas anteriores. La activación productiva continúa separada y no autorizada por esta entrega.

Para 01C-2 se necesita aprobación del alcance: resolvedor de origen verificado para `source_training_run_id`, runtime Torch offline, transformación/tokenizer/prompts exactos, score relativo y umbral fijo, resultados por muestra y validación de integridad con los mecanismos existentes. TEST no debe exigir EVALUATE previa cuando usa el umbral fijado. EXPLAIN/REPRESENT y presentación N/A en reportes deben tener alcance explícito; no se habilitan por registrar el checkpoint.

**No se inició 01C-2. Se solicita aprobación para la siguiente etapa.** Una aprobación de 01C-2 no debe confundirse con aplicar este SQL o registrar modelos en producción sin la autorización adicional solicitada para esas operaciones.
