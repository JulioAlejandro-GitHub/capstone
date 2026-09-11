# Auditoría E4 — Campañas y configuraciones persistidas

Fecha: 2026-09-11. Dictamen: **NO APROBADA**. Implementación local y pruebas sin modelos completas en el alcance descrito; aplicación de migración, integración PostgreSQL y concurrencia real **NO VERIFICADAS** por restricción de acceso al socket Docker.

## Revisión y preservación

Rama `main`, HEAD inicial/final `6b24d50ad24ea641e70e7c8b758cc93c79729d7e` (commit del usuario que incorpora E3). Árbol limpio al comenzar E4. Coincidieron **26/26 hashes** del manifiesto E3; se repitió la comprobación al validar la entrega. El cambio de HEAD respecto del informe E3 corresponde a su incorporación en Git, no a diferencias de los archivos acreditados. Ninguna prueba anterior se atribuye automáticamente a código E4.

Se leyeron instrucciones disponibles (sin AGENTS.md aplicables en repositorio/ancestros), auditoría 0A, contrato 0B v1.1, cierres E1/E2, informe/manifiesto/cierre E3, registro/resolvedor/adaptadores/contrato de entrada E2–E3, esquema histórico de experiments/models/runs, migraciones Alembic y auditoría, guardas/verificador E1 y persistencia E2. Se revisaron las políticas de instancia única, aislamiento, Alembic, backup y wrappers de migración. Se preservan informes históricos y todos los archivos del manifiesto E3.

Sólo se añaden archivos E4. La revisión efectiva es HEAD más [manifiesto E4](etapa_4_manifiesto_2026-09-11.json), con hashes de código/pruebas/migración/guía/informe; el manifiesto se excluye de sí mismo. No se hicieron commits, cambios de dependencias, servicios o permisos.

## Diseño implementado

La [guía E4](../engineering/etapa_4_campanas_2026-09-11.md) describe tablas, estados y opciones exactas.

- `experimental_campaigns`: UUID, experiment_id opcional, nombre/propósito, dataset y evidencia, requested, protocolo, código/entorno, registro, contrato canónico/hash, conteo, actor y fechas.
- `campaign_configurations`: configuración científica E2 completa, identidad por campaña/hash y requests/provenance separados. Seed se retira exclusivamente de la configuración base y pertenece a cada miembro.
- `campaign_members`: configuración exacta y semilla, posición, exclusión explícita, estado y FK de aceptación reservada.
- `campaign_attempts`: UUID, ordinal, estado, timestamps, causa y TRAIN único opcional. Reintentar no aumenta cardinalidad científica.
- `audit_events` existente: triggers transaccionales de cambios, sin journal paralelo en archivos. Actor DB y actor declarado al crear campaña se conservan con sus significados distintos.

`experiments` es agrupación opcional; no se copia su estado como campaña ni se asignan campañas a históricos. `runs` es evidencia de ejecución; el ledger de planificación no sustituye sus resultados. Los TRAIN se vinculan sólo mediante ID explícito y coincidencia de dataset/snapshot, configuración E2, seed, versiones y código/entorno relevante, con restricción adicional de experiment si fue seleccionado. No se buscan por fecha, arquitectura ni proximidad.

La canonicalización `campaign_json_v1` ordena claves, conserva orden de listas, exige tipos JSON y números finitos, normaliza floats integrales a int y codifica UTF-8 sin reinterpretar strings. El hash científico excluye seed/IDs/fechas accidentales mediante un esquema explícito, conserva todos los parámetros resueltos y no sustituye su contenido. La versión del registro se identifica por snapshot/hash de descriptores. La consulta del contrato congelado no importa el registro ni lee archivos de configuración actuales.

La expansión usa únicamente E2 (`resolve_config`, perfil batch), descriptores habilitados entrenables y optimizadores declarados. Captura loss, augmentation, regularización, fases, selección, ES y contrato de entrada E3. Las decisiones clínicas al congelar provienen del protocolo explícito; no se aceptan contradicciones con variantes. `evaluate_best_on_test` se fija a false. Los defaults que se muestran en inspección son un preview E2, no un protocolo científico aprobado.

La creación exige UUID explícito y llama al wrapper E1. Congelar revalida el mismo UUID y referencia de evidencia, compara snapshots y código/entorno, bloquea el borrador y materializa toda la matriz en una única transacción. Los eventos de verificación E1 tienen su transacción propia y pueden existir si luego falla la planificación; no se confunden con una campaña congelada exitosa. No se abre otro split ni se elige la última versión.

## Migración y protección transaccional

Alembic `20260911_01_experimental_campaigns.py`, padre `20260901_01`. Cuatro tablas nuevas, índices, PK/FK/unicidad, funciones/triggers; no backfill ni escrituras históricas. Se añade a runs un trigger que impide modificar identidad/configuración/dataset/entorno de TRAIN ya vinculados. Los FK usan RESTRICT: no borrado en cascada de entidades operativas.

El SQL se revisó y renderizó mediante Operations/MigrationContext offline en prueba, sin invocar una base alternativa. El historial Alembic resulta lineal: **22 revisiones, head único 20260911_01**. Renderizado offline no equivale a ejecución/validación de PL/pgSQL en PostgreSQL.

La congelación contrasta el JSON completo con configuraciones y miembros relacionales, snapshot/evidencia, protocolo, entorno, registro, cardinalidad y cuadrícula configuración×seeds. Guarda contenido, canonical text y SHA-256 en la misma transacción. La configuración y matriz congeladas son inmutables; la identidad de un miembro no cambia con sus intentos. Las funciones se vinculan al search_path del schema de instalación y operan como SECURITY INVOKER.

Estados: draft/frozen/active/paused/finalized para campaña; pending/active/failed/interrupted/completed/excluded para miembros; active/failed/interrupted/completed para operaciones de intento. `verified` y accepted_attempt_id se reservan a E5 y están bloqueados en E4. Completed es una declaración de cierre técnico con TRAIN vinculado, no verificación de artefactos o éxito clínico. Finalized exige ausencia de pending/active, pero admite faltantes terminales declarados.

Un índice parcial impide dos intentos activos por miembro. Locks de campaña/miembro serializan ordinal y creación; los estados del miembro siguen al último intento mediante trigger. El presupuesto limita reintentos. No se implementan scheduling, leases, workers ni recuperación automática. La política de aceptación futura sólo admite `first_verified_attempt`, no selección por métrica.

## Protocolo y límites científicos

El borrador puede conservar decisiones pendientes. Congelar exige objetivo, métricas/definiciones, targets clínicos, ranking y desempates, checkpoint/threshold, ES, algoritmo/población de calibración, presupuesto, política de faltantes/reintentos/fallback, acceso TEST, agregación/incertidumbre versionadas y declaración de VAL compartida. Rechaza roles TEST de selección/calibración, independencia de calibración falsa y exposición TEST inédita sin evidencia disponible. Sólo se admiten roles existentes train/val/test, sustentados por conteos E1.

No se fijó protocolo operativo ni se creó campaña operativa. El UUID usado en E1 no se reutilizó automáticamente. Los números de protocolo en tests son decisiones sintéticas para validar el software; no son defaults clínicos ni autorización de campaña. El cálculo de ranking/incertidumbre sigue en E7, la ejecución en E5 y el cierre integral de consumidores en E6.

## Matriz requisito → prueba → evidencia

| Requisito / escenario | Prueba o comprobación | Evidencia real |
| --- | --- | --- |
| CAMP-01 / S08–S09 | expansión de 12/36, seed duplicada, requested/resolved/contrato E3 | Local PASS; persistencia completa en PostgreSQL pendiente |
| CAMP-01 / S04 | descriptor sintético habilitado cambia nuevas matrices a 16, plan previo intacto | Local PASS, sin construir modelo |
| CAMP-02 / S14 | identidad/configuración sin seed, miembros únicos, intentos/ordinal/cause/TRAIN | Canonicalización local PASS; flujo de intentos SQL preparado, NO VERIFICADO |
| CAMP-03 / S23 | transiciones inválidas, congelación atómica, mutación congelada rechazada | Guardas locales PASS; triggers/fallo inyectado SQL NO VERIFICADOS |
| DATA-01 / DATA-02–04 | UUID obligatorio, conflicto dataset, snapshot inmutable, wrapper E1 vigente | Local PASS; no nueva acreditación operativa dataset ni campaña |
| TRACE-01 | configuración E2 completa, hash científico sensible, input E3 preservado | Local PASS; asociación TRAIN con seed/config/dataset/entorno incompatibles en prueba SQL pendiente |
| TRACE-04 / S30 | reconstrucción sin registro/configs y persistencia SQL sin sidecars | Import/validación local PASS; proceso nuevo consultando fixtures PostgreSQL preparado, NO VERIFICADO |
| TRACE-04 / S31 | error BD sanitizado sin archivos; rollback de congelación parcial | Error local PASS; fallo de miembro/auditoría transaccional y ausencia después de rollback SQL pendientes |
| EVAL-01 mínimo | selección/calibración sólo VAL, targets explícitos, VAL compartida, sin TEST en TRAIN | Validación local PASS, no predict/fit ejecutados |
| EXEC-01–02 base | intento activo único, locks, ordinal y presupuesto, ledger separado | Implementado; concurrencia real de dos conexiones NO VERIFICADA |
| Preservación / selección manual | 26 hashes E3, diff exclusivamente aditivo E4, ausencia de llamadas de modelo/publicación | Comprobado localmente; sin mutaciones operativas |

No se presenta un mock como integración ni una revisión de SQL como prueba de constraints ejecutados.

## Pruebas locales ejecutadas

Desde `malaria_dl_local_project`:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest \
  -q -p no:cacheprovider --basetemp=/private/tmp/e4-delivery \
  tests/test_campaigns_e4.py tests/test_campaigns_postgres.py \
  tests/test_governed_dataset_contract.py \
  tests/test_model_registry_e2.py::test_lazy_cli \
  tests/test_model_registry_e2.py::test_matrix_and_identical_child_resolution \
  tests/test_model_registry_e2.py::test_invalid_config_before_adapter \
  tests/test_model_registry_e2.py::test_precedence_requested_resolved_and_tracking
```

Resultado final: **61 passed, 11 skipped in 0.43s**. Las once omisiones son los casos PostgreSQL opt-in de E4. No se suman pasadas repetidas como casos nuevos. Iteraciones previas locales pasaron 34, 38, 39 y finalmente el conjunto consolidado de 61 conforme se añadieron casos; no se atribuyen sus tiempos a la revisión final.

Los 61 casos son 44 de E4 y 17 de regresión pura E1/E2. Se seleccionaron explícitamente las pruebas sin construcción/entrenamiento/inferencia; no se ejecutó la suite técnica E3 de modelos. La regresión no significa reejecución de las integraciones E1/E2/E3, que conservan sus evidencias anteriores.

También: ruff en todos los Python nuevos, AST, `git diff --check` y linealidad Alembic sin errores. Inspección de nuevos módulos sin llamadas a fit/predict/create_all ni escritores de resultados. Cero CSV en el temporal final. Los JSON temporales de tests son solicitudes de entrada, no journals o resultados de campaña.

## PostgreSQL, aislamiento y comandos pendientes

Intentos realizados por el agente:

```sh
docker compose exec -T backend python -m alembic current

docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE4_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaigns_postgres.py
```

Ambos quedaron bloqueados antes de acceder a BD: `permission denied while trying to connect to the docker API` (socket local, salida sanitizada). La segunda invocación ocurrió antes de añadir los últimos cinco casos SQL; no ejecutó ningún caso y no se atribuye a ella validación de esa revisión. La suite final contiene once casos, todos omitidos localmente por falta de opt-in/acceso.

No se interpreta acceso denegado como BD caída. El destino permitido sigue siendo Compose db:5432; la identidad/revisión instalada actual no fue revalidada. El antecedente E1–E3 de base `malaria_experiments`, schema public y revisión 20260901_01 no sustituye el precheck E4. No se cambió el socket, se arrancaron servicios, se instaló otra BD ni se aplicó la migración.

La prueba SQL implementada distingue:

1. Lectura READ ONLY de revisión instalada, tablas nuevas, índice y trigger de runs en public.
2. Migración E4 real aplicada mediante Alembic Operations en schema `capstone_test_e4_<uuid>` validado, con tablas padre sintéticas y copia aislada de audit_events/append-only. Se ejercitan los nuevos triggers/FK/índices reales de E4; no todos los constraints de padres operativos.
3. Transacción externa con savepoints para los casos habituales; rollback de DDL, fixtures y auditoría; conexión posterior READ ONLY verifica que el schema desapareció. Fallo del miembro 4 debe dejar borrador sin configuraciones/miembros parciales ni auditoría parcial.
4. Excepción deliberada para concurrencia: se hace commit sólo del schema/fixtures sintéticos, dos conexiones con PIDs distintos esperan una barrera y compiten por el mismo miembro; se exige una creación y un rechazo. Otro proceso lee toda la campaña con lecturas de archivos bloqueadas. Cleanup elimina exclusivamente el schema validado y verifica ausencia. Si un commit tiene resultado incierto o queda schema tras rollback, se registra el fallo y se intenta cleanup del schema propio; no se oculta el diagnóstico.

La prueba de concurrencia no simula dos sesiones con un solo savepoint. Tampoco representa workers/leases E5. Su eventual aprobación acreditará visibilidad entre sesiones/proceso del fixture aislado, no durabilidad de campañas operativas, reinicio del servidor ni recuperación ante pérdida de conexión. Hoy toda esa ejecución permanece NO VERIFICADA.

Secuencia reproducible para el usuario, desde la raíz y tras revisar el SQL aditivo:

```sh
make db-migrate-check
docker compose exec -T backend python -m alembic upgrade 20260901_01:20260911_01 --sql
make db-migrate

docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE4_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaigns_postgres.py
```

El wrapper de migración versionado incluye comprobación de identidad/firma/current/head, backup custom con verificación pg_restore --list, preflight transaccional/rollback y upgrade. No continuar si falla; no sustituirlo por downgrade, create_all o DDL manual. Se esperan current=head=20260911_01 y **11 passed**, además de comprobación de `/ready` conforme al procedimiento del proyecto. Cualquier fallo conserva E4 NO APROBADA hasta corregir y verificar la revisión efectiva.

## Cierre y pendientes

| Área | Estado |
| --- | --- |
| Implementación local E4 | COMPLETADA en el alcance de planificación/base de intentos descrito |
| Pruebas locales aisladas | APROBADAS: 61 |
| Migración operativa | PREPARADA; no aplicada por esta sesión, instalación actual NO VERIFICADA |
| Integración PostgreSQL E4 | NO VERIFICADA: 11 casos pendientes |
| Concurrencia DB | IMPLEMENTADA y prueba preparada; NO VERIFICADA |
| Decisiones científicas D5/D7 | no definidas para campaña operativa; borradores admiten pendientes, freeze los rechaza |
| Puerta E4 | **NO APROBADA** por persistencia/migración/concurrencia críticas pendientes |

No se crearon campañas, runs ni eventos operativos; no se ejecutó ningún modelo ni se alteraron dataset, split, constantes del proyecto split, imágenes, históricos, checkpoints, publicaciones o selección manual de Producción Etapa 2. No se inicia E5 ni se autoriza una campaña científica por disponer de esta implementación.
