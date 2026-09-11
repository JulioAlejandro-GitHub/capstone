# E4 — Planificación de campañas en PostgreSQL

## Alcance y fuentes de autoridad

`python -m src.campaign` planifica y consulta; nunca invoca TRAIN, fit, predict, EVALUATE, EXPLAIN ni publicación. `run_train_all_models.py` conserva su interfaz E2; no se añadió un `--campaign-id` sin ejecución implementada. El ejecutor por campaña corresponde a E5.

| Entidad | Identidad y contenido | Autoridad |
| --- | --- | --- |
| `experimental_campaigns` | UUID, nombre/propósito, dataset y evidencia E1, solicitud, protocolo, entorno/código, registro, contrato canónico/hash, actor y fechas | planificación científica congelada y estado de campaña |
| `campaign_configurations` | PK `(campaign_id, configuration_hash)`; configuración E2 completa sin seed, requests/provenance por variante | configuración exacta, no relectura de defaults |
| `campaign_members` | UUID, campaña/configuración, seed, posición, exclusión prevista, estado e intento aceptado reservado | repetición científica prevista |
| `campaign_attempts` | UUID, miembro/ordinal, estado, timestamps, causa y TRAIN opcional único | historial de intentos, no repeticiones adicionales |
| `audit_events` existente | cambios de las cuatro entidades mediante triggers, misma transacción | auditoría append-only; actor DB y contenido antes/después |

`experiments` sigue como agrupación descriptiva opcional por FK; no se clona su contenido ni se usa como ledger paralelo. `runs` conserva la ejecución TRAIN y sus resultados. La relación campaña→miembro→intento→TRAIN es explícita, nunca inferida por fecha o nombre. La configuración científica canónica viene del snapshot E2 del TRAIN; el catálogo `models` no se convierte en otro resolvedor.

Un cambio de seed crea otro miembro. Un reintento conserva miembro y seed, incrementando ordinal. PK/FK, unicidad `(campaña,configuración,seed)`, `(campaña,posición)`, `(miembro,ordinal)`, TRAIN único e índice parcial de un intento activo protegen esas identidades. Un TRAIN vinculado debe concordar en dataset/snapshot, configuración E2 sin seed, seed, arquitectura/adaptador/esquema y entorno/código relevante; si la campaña tiene `experiment_id`, éste también debe coincidir.

## Canonicalización y reconstrucción

`campaign_json_v1`: objetos con claves string ordenadas, UTF-8 exacto sin normalización Unicode, arrays ordenados, sin NaN/infinito ni tipos fuera de JSON. Flotantes integrales se normalizan a enteros, incluyendo -0.0 a 0; el resto utiliza serialización JSON de Python. Seeds se deduplican y ordenan antes de expandir; modelos/optimizadores/variantes tienen orden estable. La posición resultante sí forma parte del plan.

El hash científico incluye `schema_version`, arquitectura, versión del adaptador y `resolved` E2 completo: modelo, optimizador, ejecución, recipe, selección y contrato de entrada E3. Sólo se retira `resolved.execution.seed`, representado explícitamente por miembro. IDs/fechas accidentales no entran en ese hash; no se eliminan arbitrariamente campos del JSON del usuario. Requests y procedencia se conservan aparte, completos. Dos variantes equivalentes que duplicarían un miembro se rechazan, no se fusionan silenciosamente.

El contrato de campaña incluye dataset/evidencia, protocolo, entorno, solicitud y matriz completa. Se guarda contenido, representación canónica y SHA-256. Los hashes permiten comparar y detectar inconsistencias; no prueban calidad científica. La versión efectiva del registro es su snapshot de descriptores y hash, no un segundo registro editable.

La consulta usa sólo PostgreSQL y validadores de contenido: no importa el registro ni lee configs de modelos. `member_configuration(configuration, seed)` reconstruye la configuración efectiva de la repetición desde el snapshot persistido. Crear una campaña nueva sí usa el registro/resolvedor E2 vigente. VGG16 mantiene `vgg16_imagenet` de E3.

## Estados y transacciones

Campaña: `draft → frozen → active ↔ paused → finalized`; también `frozen → paused`. Finalizar requiere todos los miembros fuera de pending/active. No equivale a completitud científica o resultados verificados.

Miembro: `pending`, `active`, `failed`, `interrupted`, `completed`, `excluded`; `verified` e `accepted_attempt_id` están reservados a verificación E5 y E4 los bloquea. `completed` indica cierre técnico declarado del intento, todavía sin acreditación de artefactos. `excluded` sólo nace de una exclusión explícita planificada con causa. El estado del miembro se deriva mediante trigger del último intento; no se permite escribir un estado contradictorio.

Intento: creación en `active` desde miembro pending/failed/interrupted; `active → failed|interrupted|completed`. Fallo/interrupción requieren causa. Completed requiere TRAIN vinculado, pero no acredita por sí mismo el checkpoint. Terminales no se reescriben. Los reintentos respetan presupuesto; no se reintenta un miembro completed como si fuera otra repetición. La futura aceptación está especificada como `first_verified_attempt`, jamás mejor métrica; E4 no implementa la verificación ni permite asignar ese campo.

La congelación bloquea la campaña, compara la versión del borrador validado, inserta configuraciones/miembros y cambia estado/hash en una transacción. Los triggers contrastan matriz relacional y contrato completo, cardinalidad configuración×semillas y evidencia dataset. Un fallo, incluso de auditoría o durante inserción del miembro, revierte todo. Un error posterior de lectura devuelve error explícito, no una respuesta de congelación exitosa ni un archivo de recuperación; se puede consultar la identidad en BD.

Tras congelar se protege todo el contrato; sólo estado operativo/fecha de actualización cambian por transiciones válidas. Las filas de configuraciones y la identidad de miembros no mutan. La escritura de intentos serializa por lock de campaña y miembro, además del índice parcial. Es exclusión transaccional breve, no scheduling, leases ni recuperación de workers. Estos últimos pertenecen a E5.

La verificación E1 al crear y revalidar antes de congelar usa transacciones de lectura y el wrapper de auditoría E1; nunca se declara READ ONLY ese wrapper. Su evento de verificación puede persistir aunque falle posteriormente la transacción de planificación. El contrato conserva la referencia inicial acreditada; el evento de revalidación identifica esa referencia mediante `expected_evidence_id`.

## Solicitud de matriz y protocolo

Archivo de entrada de ejemplo `matrix-request.json` (solicitud, no journal ni persistencia de campaña):

```json
{
  "models": null,
  "optimizers": null,
  "seeds": [11],
  "variants": [{"name": "base", "selected": {}, "by_model": {}}],
  "exclusions": []
}
```

`null` en modelos/optimizadores significa capacidades entrenables habilitadas del registro. No significa dataset implícito. `selected` y `by_model` son overrides estrictos E2; el optimizador procede de la dimensión de matriz. Seed sólo se acepta en `seeds`. Una exclusión tiene `model`, `optimizer`, `variant`, `reason` y conserva los miembros previstos como excluded. Combinaciones incompatibles o exclusiones sin coincidencia se rechazan.

Un protocolo borrador puede ser `{"pending":["Definir objetivos clínicos y análisis"]}`. Congelarlo exige todas estas decisiones, sin reemplazar pendientes por .98 u otros defaults históricos:

| Campo | Contrato |
| --- | --- |
| version, objective | strings no vacíos |
| metrics | primary/secondary (listas), definitions_version, compliance (`point_estimate` o `confidence_bound`) |
| sensitivity_target, specificity_minimum | números explícitos [0,1] |
| roles | train=train, selection=val, calibration=val, final_test=test; soportados por conteos E1 |
| ranking | partition=val, criteria, tie_breaks explícitos |
| checkpoint | policy/monitor/mode aceptados por E2; threshold=.5 del contrato técnico E2 |
| early_stopping | enabled, monitor, mode, patience, min_delta, restore_best_weights explícitos |
| calibration | algorithm=`none` o `threshold_grid`, population=val, version |
| budget | max_members, max_attempts_per_member (enteros positivos) |
| missing/retries/fallback | `report_all_members` / `first_verified_attempt` / `diagnostic_only` |
| test_access | `final_only_after_candidate_lock` |
| aggregation, uncertainty | cada uno `{version, specification}` explícito; su cálculo se implementa en E7 |
| limitations | shared_val (limitación escrita), independent_calibration=false, test_exposure=`unknown` o `previously_accessed` |
| pending | lista vacía al congelar |

El sello E1 no acredita una exposición TEST inédita: no se admite afirmar independencia no demostrada. Selección/calibración comparten VAL, con limitación explícita. No se genera otra partición. El protocolo aporta targets/políticas a E2 y fuerza `evaluate_best_on_test=false`; cualquier override contradictorio falla. TEST sólo se podrá abrir en la fase final futura, no al congelar ni crear intentos. El fixture `tests/test_campaigns_e4.py::protocol` muestra el formato completo con valores exclusivamente sintéticos, no una recomendación científica.

El snapshot de entorno no inicializa TensorFlow: captura versiones instaladas, Python, commit si está disponible, variables de determinismo y hash de fuentes/configs siguiendo E2. Si cambia antes de congelar, se exige un nuevo borrador. La compatibilidad al reanudar corresponde a E5, no a ignorar esas diferencias.

## CLI y servicio implementados

Desde `malaria_dl_local_project`, tras disponer de las entradas del usuario:

```sh
# Inspección: no conecta a BD ni acredita que el protocolo esté listo.
python -B -m src.campaign inspect --request matrix-request.json

# Creación explícita: escribe campaña y evidencia E1, pero no intentos ni TRAIN.
python -B -m src.campaign create --request matrix-request.json \
  --protocol protocol-draft.json --dataset-version-id "$DATASET_VERSION_ID" \
  --name "Campaña propuesta" --purpose "Comparación definida por el usuario" --actor "$ACTOR"

python -B -m src.campaign edit --campaign-id "$CAMPAIGN_ID" \
  --request matrix-request.json --protocol protocol-complete.json
python -B -m src.campaign validate --campaign-id "$CAMPAIGN_ID"
python -B -m src.campaign freeze --campaign-id "$CAMPAIGN_ID" \
  --dataset-version-id "$DATASET_VERSION_ID"
python -B -m src.campaign show --campaign-id "$CAMPAIGN_ID"
```

Para operación, ejecutar esos argumentos con el prefijo autorizado `docker compose exec -T -w /app/malaria_dl_local_project backend`. Los IDs deben ser explícitamente designados para la nueva planificación: el UUID histórico de E1 no es un default ni autoriza estas escrituras. `validate` es lectura: en borrador valida completitud y resuelve la matriz; en congelada devuelve el contrato almacenado. `show` reconstruye campaña, miembros e intentos desde BD. No se escriben archivos de resultados; la CLI imprime la respuesta.

Operaciones programáticas mínimas en `CampaignRepository`: `create_attempt(campaign_id, member_id)`, `update_attempt(campaign_id, attempt_id, training_run_id=...)`, `update_attempt(..., state='failed'|'interrupted'|'completed', cause=...)`, `transition(campaign_id, state)` y `get(campaign_id, dataset_version_id=None)`. No descubren TRAINs ni ejecutan modelos. El borrador permite edición de solicitud/protocolo; una modificación científica tras congelar exige otra campaña.

## Migración y verificación operativa pendientes

Revisión aditiva `20260911_01`, padre `20260901_01`: cuatro tablas, índices, FKs y triggers. No contiene backfill, seeds ni actualización de filas históricas. Añade un trigger a runs que protege sólo identidades ya vinculadas a intentos. FKs RESTRICT pueden impedir purgas posteriores de entidades referenciadas; no se cambia la política de purga ni se prueban downgrades sobre datos operativos.

Desde la raíz, con acceso a Compose, revisar primero SQL/identidad y seguir el wrapper existente:

```sh
make db-migrate-check
docker compose exec -T backend python -m alembic upgrade 20260901_01:20260911_01 --sql
make db-migrate
```

`make db-migrate` comprueba current/head y firma histórica, crea backup custom, lo verifica con `pg_restore --list`, ejecuta preflight transaccional con rollback y sólo entonces aplica upgrade. Detenerse si falla cualquiera de esos pasos. No sustituirlos por un upgrade manual. Comprobar current=head y `/ready` según el procedimiento del proyecto tras migrar.

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE4_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaigns_postgres.py
```

Se esperan **11 casos aprobados**. Uno inspecciona instalación public mediante READ ONLY. Los demás ejecutan la migración real en un schema `capstone_test_e4_<uuid>` con padres sintéticos y copia aislada de auditoría, sin writes científicos en public. La mayoría revierte toda la transacción externa. El caso concurrente publica únicamente fixtures del schema aislado para dos conexiones simultáneas (PIDs distintos), comprueba una sola creación y reconstrucción en un proceso nuevo; cleanup elimina sólo ese schema validado. Una limpieza fallida se reporta, no se oculta.

Estas pruebas distinguen constraints nuevos reales, padres sintéticos y lectura de instalación operativa. No certifican todos los constraints históricos de public.runs ni durabilidad de una campaña operativa. En esta sesión no pudieron ejecutarse por restricción del socket Docker: véase el [informe E4](../audits/etapa_4_campanas_2026-09-11.md).
