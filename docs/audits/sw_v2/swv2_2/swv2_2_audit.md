# SWV2.2 — Auditoría del sistema de campañas y contratos

Realizada sobre el código real (HEAD `2ba0755`) y el esquema congelado `alembic_v2/baseline` **antes** de modificar código. `S/` = `malaria_dl_local_project/src/malaria_dl/`.

## 1. Estado real encontrado

| Componente | Hallazgo |
|---|---|
| Motor E4 de campañas | Completo y vigente: `S/campaigns/contracts.py` (`expand_matrix`, `validate_protocol`, `validate_frozen_contract`, `canonical`/`digest`), `S/campaigns/service.py` (`create`, `freeze`, `planning_environment`), `S/campaigns/repository.py`. Crear y congelar eran **dos transacciones** (draft persistido, luego freeze). |
| Model registry | `S/models/registry.py`: `ModelDescriptor` (id, aliases, enabled, trainable, version, adapter, config_path, strategies, optimizers, preprocessing). Habilitados: `custom_cnn` (1.0), `vgg16` (1.1, alias `vgg16_transfer_learning`), `densenet121` (1.0). Es el mecanismo de discovery; la tabla `models` sólo aporta UUID relacional. |
| Configuración | `S/models/configuration.py::resolve_config`: defaults versionados `configs/models/<id>.json` < perfil `batch` < selected < overrides; valida dominios y reglas cruzadas. |
| Optimizers | `S/models/optimizers.py`: `OPTIMIZER_DEFAULTS` = adam, adamw, sgd, adadelta (dominio cerrado) + `BATCH_LEARNING_RATES`. |
| Protocolo científico | `configs/science/e7_v1.json` (hash `7db076d7…`) → `S/science/protocol.py::campaign_plan` produce request + protocolo E4 aprobado `capstone_science_e7_v1`. |
| Ejecutor | `run_train_all_models.py::main` delega desde Etapa 5 (commit `15f2c95`) en `S/execution/campaign.py::main`: `--campaign-id` obligatorio; ejecutar exigía además `--dataset-version-id` (`EXPLICIT_DATASET_REQUIRED`). |
| Modo directo histórico `--dataset-version-id` | **No existe en HEAD**: argparse falla con `--campaign-id required`. El test preexistente `test_model_registry_e2::test_matrix_invalid_combination_rejected_before_preflight` lo acredita (falla antes y después de SWV2.2). No se recreó: TRAIN sin campaña no forma parte del contrato actual. |
| Backend/API | No había rutas de campañas (sólo `assessments` filtra por campaign_id). |
| Frontend | No había UI de campañas. Menú Modelo IA: Resumen, Ejecuciones, Dataset, Datasets y modelos. |
| PostgreSQL v2 | `experimental_campaigns`, `campaign_configurations`, `campaign_members`, `campaign_attempts` con guardas `campaign_guard`, `campaign_configuration_guard`, `campaign_member_guard`, `campaign_audit`, CHECK `ck_campaign_frozen_required_v2`, `campaign_contract_valid`, `campaign_configuration_valid`. GRANT SELECT/INSERT/UPDATE/DELETE a `capstone_v2_runtime`; DELETE bloqueado por trigger (`CAMPAIGN_DELETE_FORBIDDEN`). Filas al inicio: 0. |

## 2. E10.PRE11 contrastado con PostgreSQL v2

| PRE11 | Situación en v2 / SWV2.2 |
|---|---|
| Campaña `3acf89b7…` paused, 36 miembros, 7 runs legacy | No existe en v2 (base limpia, 0 campañas). No se reconstruyó. |
| Matriz = modelos × optimizadores × variantes, semillas compartidas | Se conserva exactamente: SWV2.2 usa `expand_matrix` como única fuente del total. |
| Protocol policy (checkpoint, EarlyStopping, objetivo, calibración) se impone a todas las configuraciones; conflicto → rechazo | Conservado: EarlyStopping y objetivo clínico son de campaña, no por modelo. |
| H1 schema no E10 | Resuelto por v2: `require_e10_schema` = PASS. |
| `_create_run` exige `models.id` único por nombre | Vigente; tabla `models` vacía en v2 ⇒ el plan lo reporta (`model_catalog_identity` FAIL) para SWV2.3. |
| H4 archivos extra en directorios de dataset | Materializado: 4 `.DS_Store` en la raíz del dataset hacían fallar la verificación (ver `swv2_2_operations.md` §2). |

## 3. Matriz PostgreSQL v2 → backend → API → React → CLI

| Objeto v2 | Consumidor backend | API | React | CLI | Estado / decisión |
|---|---|---|---|---|---|
| `dataset_versions` (+ materialización/checks) | `services/governed_datasets` (lista), `persistence.dataset_evidence.verify_dataset_for_execution` (guardar) | `GET /api/datasets` (existente) | selector Dataset Version | `repository.get` aserción | **REUTILIZAR** |
| `audit_events` (`ml.dataset_verification`) | verificador existente | — | — | — | **REUTILIZAR** (evidencia exigida por `campaign_guard`) |
| `experimental_campaigns` | `CampaignRepository.create_frozen` (nuevo), `get` | `POST /api/campaigns`, `GET /api/campaigns/{id}` | guardar / recarga | `--campaign-id`, `--plan` | **ADAPTAR** (crear+congelar atómico, idempotente) |
| `campaign_configurations` | `_materialize` (extraído de `freeze`) | incluido | resumen | plan | **ADAPTAR** (sin cambio de SQL) |
| `campaign_members` | `_materialize` | incluido | "Total de Experimentos" | plan `experiments` | **REUTILIZAR** nombre interno; UX = experimentos |
| `campaign_attempts`, `runs`, `train_execution_*` | ejecutor E5 | — | — | ejecución | **FUERA DE ALCANCE** (SWV2.3) |
| `models` | `_create_run` | — | — | readiness | **FUERA DE ALCANCE** (reportado) |
| registry/descriptors | `campaigns/configuration.catalog` (nuevo) | `GET /api/campaigns/catalog` | formulario por metadata | — | **CREAR** capa de catálogo sobre lo existente |
| `expand_matrix` | `campaigns/configuration.resolve` (nuevo) | `GET /api/campaigns/preview` | total y validación | — | **REUTILIZAR** como autoridad del total |
| `run_configurations.clinical_target_recall` (>0, ≤1) | validación en `build_protocol` | — | valor fijo mostrado | — | **ADAPTAR** (dominio v2 aplicado antes de guardar) |

## 4. Inventario real de parámetros

Fuente de defaults: `resolve_config(model, None, {"optimizer": {"name": <primero>}}, batch=True)` sobre `configs/models/<id>.json` (perfil batch). Editabilidad = reglas de `resolve_config` + descriptor.

| Parámetro | Ruta | Tipo / dominio | Default custom_cnn / vgg16 / densenet121 | Alcance | Editable |
|---|---|---|---|---|---|
| input_size | model.input_shape `[n,n,3]` | int ≥32 | 200 / 200 / 200 | modelo | sí |
| weights | model.weights | enum none, imagenet (sólo con fine_tuning) | none / imagenet / imagenet | modelo | vgg16, densenet121 |
| preprocessing | model.preprocessing | enum descriptor | rescale_0_1 / vgg16_imagenet / rescale_0_1 | modelo | no (1 opción) |
| dropout | model.dropout | [0,1) | 0.4 / 0.5 / 0.5 | modelo | sí |
| l2 | model.l2 | [0,1); 0 fijo si default 0 | 0.0001 / 0 / 0 | modelo | custom_cnn |
| head_units | model.head_units | fijo | 128 / 1024 / 0 | modelo | no |
| batch_normalization | model.batch_normalization | fijo | train / absent / inference | modelo | no |
| fine_tune_layers | model.fine_tune_layers | int 0..default | 0 / 4 / 4 | modelo | vgg16, densenet121 |
| max_epochs | execution.max_epochs | int ≥1 | 100 / 100 / 100 | modelo | sí |
| fine_tune_epochs | execution.fine_tune_epochs | int ≥0 (requiere capas >0) | 0 / 20 / 20 | modelo | vgg16, densenet121 |
| batch_size | execution.batch_size | int ≥1 | 64 | modelo | sí |
| deterministic_ops | execution.deterministic_ops | bool | false | modelo | sí |
| no_augment | execution.no_augment | bool | false | modelo | sí |
| reject_prediction_collapse | execution.reject_prediction_collapse | bool | true | modelo | sí |
| min_class_fraction | execution.min_class_fraction | [0,0.5] | 0.05 | modelo | sí |
| optimizer | optimizer.name | enum adam, adamw, sgd, adadelta | — | **campaña** (request.optimizers) | sí |
| learning_rate / fine_tune_learning_rate | optimizer.* | BATCH_LEARNING_RATES: adam/adamw 1e-4/1e-5, sgd 1e-3/1e-4, adadelta 1/1 | — | por optimizador | no (ver nota) |
| betas, epsilon, momentum, rho, weight_decay, clipping, EMA… | optimizer.parameters | OPTIMIZER_DEFAULTS | — | por optimizador | no (ver nota) |
| seeds | request.seeds | int 0..2147483647, únicos | 11, 29, 47 (`e7_v1.json`) | **campaña** | sí |
| early_stopping.enabled / patience / min_delta / restore_best_weights | protocol.early_stopping | bool / int ≥0 / num ≥0 / bool | true / 12 / 0.0001 / true | **campaña** | sí |
| early_stopping.monitor / mode | protocol | — | val_f2_parasitized / max | campaña | no (protocolo) |
| checkpoint policy/monitor/mode/threshold | protocol.checkpoint | — | auc_with_min_recall / val_f2_parasitized / max / 0.5 | campaña | no |
| sensitivity_target (→ target_recall, min_recall, clinical_target_recall) | protocol | (0,1] por v2 | 0.98 (`e7_v1.json` objective.value) | campaña | no |
| specificity_minimum, calibration, test_access | protocol | — | 0 / none / final_only_after_candidate_lock | campaña | no |
| budget.max_attempts_per_member | protocol.budget | int ≥1 | 3 | campaña | sí |
| budget.max_members | protocol.budget | = Total de Experimentos | derivado | campaña | derivado |
| beta, recipe (loss, metrics, augmentation, reduce_lr), evaluate_best_on_test | — | fijos (F2_REQUIRES_BETA_2, UNSUPPORTED_RECIPE_CHANGE, TEST prohibido) | — | — | no |

Nota optimizadores: en el contrato E4 los overrides de una variante se aplican a **todos** los optimizadores de la matriz; sus hiperparámetros son específicos de cada optimizador (p. ej. `momentum` sólo existe en SGD), por lo que exponerlos por modelo exigiría inventar un producto nuevo. Se muestran (LR base/fine-tuning) y siguen siendo los defaults versionados; no se elimina ningún parámetro del sistema.

## 5. Modelos descubiertos

`custom_cnn` (Custom CNN, adapter 1.0, base), `vgg16` (VGG16, 1.1, base + fine_tuning), `densenet121` (DenseNet121, 1.0, base + fine_tuning). Etiquetas de presentación en el backend; un modelo registrado sin etiqueta se muestra por su id. Prueba de extensibilidad: registrar un descriptor adicional lo agrega a catálogo, preset y matriz (3→4 modelos, 36→48 experimentos) sin cambiar campañas ni React (`test_new_registered_descriptor_needs_no_campaign_change`). U-Net **no** implementado ni registrado. Nota para el futuro: `run_configurations.architecture` tiene CHECK `IN ('custom_cnn','vgg16','densenet121')` en v2; entrenar una arquitectura nueva requerirá una evolución de esquema en su propia fase (no afecta a la configuración de campañas).

## 6. Contratos

**Dataset version.** Fuente: `GET /api/datasets` (gobernado). Seleccionable sólo si `FROZEN` y `trainable`; preselección únicamente si existe exactamente una versión entrenable (no hay UUID hardcodeado). Al guardar, `verify_dataset_for_execution` (consumer `campaigns.configure`) verifica fingerprints e integridad física y persiste la evidencia exigida por `campaign_guard`. `campaign.dataset_version_id` es la única fuente de verdad del dataset.

**Campaña (`campaign_configuration_v1`).** Documento del operador: `models`, `optimizers`, `seeds`, `variants[{name, parameters{model_id:{key:value}}}]`, `protocol{early_stopping{…}, budget{max_attempts_per_member}}` + `campaign_id` (clave idempotente generada por el cliente), `name`, `purpose`, `dataset_version_id`. Traducción única: `S/campaigns/configuration.resolve` → request E4 (`by_model` explícito por parámetro editable) + protocolo E4 (aprobado + valores del operador; `version` aprobada sólo si el protocolo resultante es idéntico al aprobado, si no `campaign_configuration_v1:<sha256>`). Persistencia: `CampaignService.configure` → `CampaignRepository.create_frozen`: draft + configuraciones + miembros + freeze en **una** transacción (en HTTP, la misma que el evento de auditoría de aplicación). Reintento con mismo `campaign_id` y mismas decisiones → misma campaña; decisiones distintas → `409 CAMPAIGN_ID_CONFLICT`. Preset adicional "Plan científico aprobado capstone_science_e7_v1" reproduce exactamente los 12 `configuration_hash` y el protocolo de `e7_v1.json`.

**Total de Experimentos.** `expand_matrix(request, protocol, frozen=True)["expected_count"]` = configuraciones × semillas; configuraciones = modelos × optimizadores × variantes (deduplicadas por hash; variantes equivalentes se rechazan). El frontend no calcula: muestra `preview.summary.total_experiments` del backend; al guardar el backend verifica que el plan persistido tenga el mismo total (`TOTAL_EXPERIMENTS_DIVERGENCE`) y la UI recarga por `campaign_id` y compara.

**CLI.** `python run_train_all_models.py --campaign-id <UUID>` ejecuta (dataset desde la campaña); `--dataset-version-id` queda como aserción opcional (si difiere → `CAMPAIGN_DATASET_CONFLICT`); `--plan` (mutuamente excluyente con `--inspect/--resume/--result/--dry-run`) resuelve el plan y la preparación sin reservar intentos, sin escribir evidencia y sin TRAIN. Boundary: `execute_campaign → ExecutionRepository.claim → worker → TRAIN`.
