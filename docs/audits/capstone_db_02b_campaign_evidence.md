# CAPSTONE-DB-02B — Evidencia del dataset en campañas

Estado documental: `CURRENT_DOC` — **CAPSTONE-DB-02B CERRADO operativamente**. Integrado en main local, SQL instalado, campaña real y readback verificados. Publicación remota pendiente por bloqueo de revisión automática.

Las secciones anteriores a «Cierre operativo» conservan la evidencia de preparación.
Su estado histórico de autorización/aplicación queda sustituido por la última actualización de cierre.

Fecha: 2026-10-12. Base de trabajo: `55e5670` (CAPSTONE-DB-02A integrado).
Rama: `fix/capstone-db-02b`; worktree: `/private/tmp/capstone-db-02b`.
No se editó el checkout operativo en `main`, cuyos bind mounts usan recarga automática.

## Diagnóstico y límites de la evidencia

**Causa demostrada:** `public.campaign_guard()` exige literalmente `verified`;
rechaza `verified_requested_splits` aun cuando identidad y snapshot coincidan.
Se exportó y leyó la función completa vigente mediante `pg_get_functiondef`.
El único trigger que llama esa función es `campaign_guard`, BEFORE INSERT/DELETE/UPDATE,
FOR EACH ROW sobre `public.experimental_campaigns`.
La función también consulta `audit_events`, `campaign_configurations` y `campaign_members`.

Los diez eventos recientes del dataset `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`
son exitosos, sin código de error, con snapshot y estado `verified_requested_splits`.
Todos declaran `required_splits` y `physically_verified_splits` iguales a `["train","val"]`.
El más reciente observado es `dfc0346f-f843-4924-8c9a-9dd6e9d5c3ba`,
2026-10-12 14:22:55.358857 UTC (11:22:55 en Santiago), consumer `campaigns.configure`.

La consulta de logs en el intervalo 14:20–14:25 UTC confirmó:

```json
{"event":"campaign.database_error","exception_class":"RaiseException","sqlstate":"P0001","table":null,"constraint":null,"message":"CAMPAIGN_DATASET_EVIDENCE_CONFLICT","correlation_id":"4b34593b-e53a-4822-9695-ce27c8eb17ac"}
```

**No demostrado:** ese log no registra el ID de evidencia ni los parámetros de la
inserción rechazada. La proximidad temporal del evento más reciente no demuestra
que fuera el seleccionado. No se reconstruyó el payload HTTP histórico.
Entre los eventos leídos hay snapshots con `dataset_root` de Mac y de Docker:
no se presume igualdad entre todos los snapshots ni se normaliza su contenido en SQL.

**Hipótesis pendiente:** una vez corregida esta causa, el intento operativo podría
exponer otro rechazo legítimo. La creación real y su readback siguen pendientes.

**Restricciones legítimas:** evento existente y del tipo correcto, éxito, ausencia
de error, identidad del dataset, igualdad JSONB exacta del snapshot, inmutabilidad,
transiciones, hash, matriz, protocolo científico y estados iniciales. Se preservan.
La incompatibilidad real es la condición de estado, no la conexión HTTP ni un contrato
estructural de PostgreSQL.

## Trazabilidad del código y significado científico

Rutas relativas a la raíz del repositorio:

- `backend_api/app/routes/campaigns.py`: POST `/api/campaigns` y GET de detalle.
- `backend_api/app/services/campaign_configuration.py`: servicio utilizado por la ruta.
- `malaria_dl_local_project/src/malaria_dl/campaigns/service.py`, `configure()`:
  solicita una verificación nueva con `required_splits=("train", "val")`, pasa
  `snapshot.evidence_id` y `snapshot.metadata()` al contrato. No selecciona el último
  evento por fecha. `create()` y la validación de congelación tienen el mismo alcance.
- `.../persistence/dataset_evidence.py`, `verify_dataset_for_execution()`:
  genera un UUID, persiste `ml.dataset_verification`, confirma commit y readback,
  devuelve el mismo snapshot con el ID de esa evidencia.
- `.../data/governed_dataset.py`, `metadata()` y `verification_metadata()`:
  separan el snapshot científico de la cobertura verificada en esta operación.
  `_resolve()` exige metadatos congelados, huellas, materialización reconciliada y
  controles de integridad; la verificación física se limita a los splits solicitados.
- `.../campaigns/repository.py`, `create_frozen()` y `_materialize()`:
  insertan draft, configuraciones, miembros y congelación en una única transacción;
  el ID y snapshot proceden del mismo contrato. El readback se hace después del commit.
- `.../assessment/lineage.py`: verificación explícita del split de evaluación y
  autorización separada de TEST; crear una campaña no acredita acceso final a TEST.

En el productor vigente, `verified` significa verificación física de train, val y test.
`verified_requested_splits` significa verificación física de un subconjunto no vacío;
**por sí solo no implica que incluya train y val**. `verified_metadata_only` no acredita
archivos físicos. En los eventos inspeccionados se verifican train y val y se informa
`global_integrity_status=verified_frozen_metadata`; TEST solo figura en los metadatos
congelados del snapshot. No se convierte esa evidencia en una verificación física global.

TRAIN usa train/val; selección y calibración usan val. El protocolo conserva
`test_access=final_only_after_candidate_lock`. Por eso train/val bastan para configurar
la campaña, sin leer TEST ni ejecutar entrenamiento/evaluación/explicabilidad.

La prueba de servicio usa el verificador inyectado con una evidencia sintética persistida,
el servicio y repositorio reales y PostgreSQL real. Verifica que el ID fresco se transmite
y que `audit_events.after_state.snapshot = experimental_campaigns.dataset_snapshot`
y la identidad del dataset son verdaderas. Esto prueba el flujo reproducido, **no los
parámetros del intento histórico**. No se detectó motivo para modificar Python o frontend.

## Corrección mínima

[apply.sql](../../scripts/db/capstone_db_02b/apply.sql) conserva la definición completa
y sustituye únicamente la expresión que rechazaba el estado:

```sql
OR ((ev.after_state->>'integrity_status') = 'verified'
    OR ((ev.after_state->>'integrity_status') = 'verified_requested_splits'
        AND (ev.after_state->'required_splits') @> '["train","val"]'::jsonb
        AND (ev.after_state->'physically_verified_splits') @> '["train","val"]'::jsonb))
   IS DISTINCT FROM TRUE
```

El `IN` propuesto sin cobertura sería insuficiente: también aceptaría evidencias de
solo train o solo val. Esta condición mantiene el significado histórico de `verified`
y acepta el estado parcial únicamente cuando acredita la cobertura necesaria.
`IS DISTINCT FROM TRUE` rechaza estado ausente/NULL y cobertura ausente/NULL, además
de valores desconocidos. No se añade una validación estructural ni una consulta de
versión: es una regla de integridad de la evidencia en PostgreSQL.

Se mantienen firma, lenguaje, search_path, trigger, propietario y privilegios mediante
CREATE OR REPLACE FUNCTION. Las demás ramas son idénticas. No hay cambios en migraciones,
backend, frontend, datasets, métricas, predicciones o checkpoints. Se conserva DB-02A.

## Pruebas y evidencia conservada

Ejecutar desde este worktree:

```sh
make test-db02b
```

Resultado: **49 passed in 0.88s**, sin skips.
[Salida completa](capstone_db_02b/test_results.txt).

| Requisito | Resultado |
|---|---|
| 1–2: verified y verified_requested_splits con train/val | PASS: congelación, commit y readback |
| 3–8: ID inexistente, fallo, tipo incorrecto, error, dataset/snapshot diferentes | PASS: rechazo explícito |
| 9: desconocido, NULL, ausente, metadata-only, rejected | PASS |
| Cobertura insuficiente, nula o tipo incorrecto | PASS |
| 10: campaña, configuración y dos miembros persistidos | PASS |
| 10: fallo de hash después de insertar miembros | PASS: rollback de campaña, matriz y auditoría de campaña |
| 11: identidad, borrado, transiciones, draft inicial, inmutabilidad | PASS con función original y corregida |
| 11: hash, matriz, grilla de seeds, protocolo, ciencia, miembros iniciales y terminalidad | PASS con función original y corregida |
| Rollback SQL y reproducción de la causa original | PASS: misma evidencia rechazada antes y aceptada después |
| Servicio: evidencia fresca, dataset y snapshot exactos | PASS en integración sintética |
| 12: frontend operativo → POST → GET/configuraciones/miembros | PENDIENTE de autorización |

La fixture `tests/db02b/fixtures/operational_schema.sql.gz` contiene únicamente el
DDL exportado de la base vigente con `pg_dump --schema-only --no-owner --no-privileges`.
Se conserva completo para no omitir restricciones transitivas ni usar migraciones
históricas como sustituto de la estructura real. Se puede revisar con `gzip -dc`.
SHA256 del SQL descomprimido:
`4751e2c8d03be6cca1eb6f50b25b83a5493032104b3db876572909f0c8e9ac82`.
No contiene datos operativos ni credenciales. No se comparan versiones/revisiones.

Compose usa PostgreSQL 17.9 en tmpfs, red interna propia, sin puertos ni volúmenes
operativos, y el código del worktree montado de solo lectura. El alias `db` pertenece
exclusivamente a esa red de pruebas. El runner reutiliza la imagen local
`capstone-malaria-backend`. Las conexiones de prueba no aceptan una URL operativa.
Make elimina el contenedor y la red incluso si fallan las pruebas.
Las fixtures insertan exclusivamente datos sintéticos y conservan todos los triggers.
Los ensayos iniciales requirieron corregir las fixtures (unicidad, casts, catálogo y
search_path); no se cambiaron reglas operativas para conseguir el resultado.

[inspect.sql](../../scripts/db/capstone_db_02b/inspect.sql) conserva las consultas de
catálogo y evidencia como herramienta manual de auditoría, nunca importada por la app.
[Resultado de solo lectura](capstone_db_02b/readonly_evidence.txt).
La definición operativa reconsultada coincide con la exportación inicial completa;
SHA256 de esa exportación inicial: `ae7505ab6222e99b28155ed1e875457a48ba255b13e19e069ccdb228d74944ca`.

## Aplicación y reversión (requieren autorización independiente)

No se ejecutó ninguno de estos comandos sobre la base operativa. Desde el checkout
operativo que ya tiene su `.env` y Compose configurados, tras revisar y autorizar:

```sh
docker compose exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < /private/tmp/capstone-db-02b/scripts/db/capstone_db_02b/apply.sql
```

El script incluye BEGIN/COMMIT y `lock_timeout=5s`. Requiere un rol propietario de la
función o administrador. No se conceden privilegios nuevos. Si psql falla, detener la
aplicación; no continuar con la prueba frontend. La desconexión revierte la transacción
no confirmada. La ejecución repetida instala la misma definición.

Después de la aplicación autorizada, crear una campaña desde
`http://localhost/modelo-ia/campanas?datasource=malaria`, registrar el HTTP exitoso,
consultar su detalle y contrastar configuraciones, miembros, dataset, evidencia y
snapshot mediante GET y SQL de solo lectura. No ejecutar TRAIN/EVALUATE/EXPLAIN.
Estas escrituras de campaña también requieren autorización operativa.

[rollback.sql](../../scripts/db/capstone_db_02b/rollback.sql) conserva íntegra la
función original exportada y probada. Para revertir, con autorización:

```sh
docker compose exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < /private/tmp/capstone-db-02b/scripts/db/capstone_db_02b/rollback.sql
```

La reversión restaura el rechazo original para nuevas evidencias parciales. No borra
campañas ya creadas ni modifica auditorías; los drafts con evidencia parcial volverían
a ser rechazados al actualizarse. No hace falta reiniciar backend/frontend.

## Riesgos residuales y cierre

- El log histórico no permite asociar inequívocamente ID/snapshot al intento fallido.
- El test de servicio inyecta un verificador sintético; no revalida archivos científicos.
- La copia de esquema no incluye ACL/propietarios ni datos operativos; no acredita los
  permisos del rol runtime ni sustituye la comprobación frontend posterior.
- Los scripts son una intervención puntual revisable sobre la función observada; si
  otro cambio modifica la función antes de aplicar/revertir, revisar manualmente para
  no sobrescribirlo. No se incorpora ese control al software.
- La evidencia append-only se confirma antes de la transacción de campaña: un fallo
  puede dejar su evento de verificación, como ya ocurría. La atomicidad comprobada
  abarca campaña, configuraciones, miembros y auditorías generadas por esos cambios.

| Elemento | Resultado |
|---|---|
| Causa raíz | Demostrada (condición de estado) |
| Corrección implementada | Sí, en rama/worktree independiente |
| Integridad científica preservada | PASS en el alcance probado |
| Pruebas positivas | PASS |
| Pruebas negativas | PASS |
| Pruebas de regresión | PASS |
| PostgreSQL operativo modificado | No |
| TRAIN/EVALUATE/EXPLAIN ejecutados | No |
| Aplicación operativa pendiente | Sí |

**Técnicamente listo. Incidente operativo abierto.** Pendientes de autorización:
aplicación del SQL y creación/consulta de una campaña desde el frontend. No se solicita
permiso para trabajos ya completados ni se interpreta el paso de las pruebas como
aprobación de cambios operativos.


## Cierre operativo — CAPSTONE-DB-02B

Actualización: 2026-10-12, 15:01 UTC. Autorización: solicitud del usuario
«Ejecución operativa, integración Git y cierre», incluidas integración, aplicación
SQL, una campaña real y publicación de main después de comprobar integración/pruebas.

**Estado intermedio, posteriormente superado: CIERRE PARCIAL.** La corrección está instalada y verificada. No se declara cerrado
el incidente porque falta crear y recuperar la campaña mediante una sesión autenticada.
No hay acceso del agente a un navegador autenticado ni una sesión HTTP autorizada.
Se solicitó al usuario realizar únicamente esa creación desde su sesión, sin compartir
credenciales/tokens. No se generaron tokens ni se eludieron controles de acceso.

| Elemento | Evidencia |
|---|---|
| Commit de integración | `5f12f819ad7b7d14d1dc6aaad8eb5126e6260a0a` |
| Rama integrada | `fix/capstone-db-02b`, implementación `63e65da` |
| PostgreSQL antes | Coincidencia exacta con la definición original de rollback |
| SQL aplicado | Exit 0: BEGIN, SET, CREATE FUNCTION, COMMIT |
| PostgreSQL después | Coincidencia exacta con apply.sql |
| Propietario / ACL | Sin cambios: capstone_v2_migrator; EXECUTE de migrator/runtime |
| Trigger | Habilitado (`O`), BEFORE INSERT/DELETE/UPDATE en experimental_campaigns |
| Pruebas finales | 49 PASS, 0 FAIL, 0 SKIP; 0.89 s, desde main |
| Campaña creada | Pendiente de sesión autenticada; ninguna creada por el agente |
| Readback HTTP/SQL de campaña | Pendiente |
| Frontend | Pendiente; no se afirma inspección visual |
| Rollback | No requerido |
| TRAIN/EVALUATE/EXPLAIN | No ejecutados |
| Estado final | CIERRE PARCIAL: etapa E pendiente |

### Comandos y resultados

1. `git status --short`, `git branch -avv`, `git worktree list`,
   `git log --oneline --decorate -10`, `git diff --stat main...fix/capstone-db-02b`
   y `git log --oneline main..fix/capstone-db-02b`.
   Ambos checkouts limpios. No existe rama `capstone-db-02b`.
   Main estaba en `4655c44`; sus dos commits nuevos de skills se conservaron.
2. `git merge --no-ff fix/capstone-db-02b -m 'merge: integrate CAPSTONE-DB-02B campaign evidence correction'`.
   Merge `5f12f81`, sin conflictos ni cambios de código runtime; no reinicios.
3. `docker compose ps`: backend/frontend activos; PostgreSQL healthy.
   Con `PGOPTIONS='-c default_transaction_read_only=on'`, consultas administrativas
   de función, propietario/ACL, trigger y pg_stat_activity. Ninguna otra transacción
   activa detectada en la base al efectuar la comprobación previa.
4. Se exportó `pg_get_functiondef('public.campaign_guard()'::regprocedure)` y se
   comparó exactamente con el cuerpo de rollback.sql. También se confirmó que
   apply.sql difiere de rollback.sql únicamente en la condición aprobada.
5. Aplicación autorizada desde el checkout operativo:

   ```sh
   docker compose exec -T db sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < scripts/db/capstone_db_02b/apply.sql
   ```

   Exit 0 y COMMIT confirmado. No se ejecutó rollback ni DDL adicional.
6. Nueva exportación de la función y comparación exacta con apply.sql: PASS.
   Propietario, ACL y asociación/habilitación del trigger: conservados.
   La semántica NULL/desconocido/cobertura insuficiente se acredita con las pruebas
   aisladas, sin insertar evidencias artificiales en PostgreSQL operativo.
7. `make test-db02b` desde main: 49 PASS. El contenedor tmpfs y su red interna
   se eliminaron correctamente; la suite no apunta a PostgreSQL operativo.

Evidencia conservada: [comprobaciones](capstone_db_02b/operational/checks.json),
[función antes](capstone_db_02b/operational/before.sql),
[función después](capstone_db_02b/operational/after.sql),
[resultado de aplicación](capstone_db_02b/operational/apply_result.txt) y
[pruebas finales](capstone_db_02b/operational/test_results.txt).

### Pendiente específico

Desde una sesión autorizada, crear **una sola campaña**, nombre sugerido
«CAPSTONE-DB-02B — prueba operativa», con el dataset
`d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` y una configuración mínima válida.
Conservarla. Obtener su ID, comprobar POST exitoso y GET del detalle/listado;
contrastar mediante SQL la evidencia, snapshot exacto, configuraciones y miembros,
y comprobar ausencia de ejecución científica de esa campaña.
La autorización para hacerlo ya existe; falta acceso a la sesión, no una nueva aprobación.


### Publicación remota bloqueada por revisión automática

El commit documental `0770763` quedó integrado directamente en main local.
Se intentó `git push origin main` después de verificar integración, pruebas y limpieza
del checkout. La revisión automática rechazó la operación antes de ejecutarla.
Se verificó el destino configurado de origin:
`https://github.com/JulioAlejandro-GitHub/capstone.git`.
Un segundo intento presentó ese destino y la autorización literal de la sección 11;
la revisión volvió a rechazarlo por considerar no acreditada la autorización de destino
para publicar código privado y modificar la rama principal remota.

No se utilizó otra vía de publicación. Origin no recibió estos commits en esta sesión.
Se solicita confirmación directa del usuario para ese destino concreto debido al bloqueo
impuesto por la revisión automática. Este bloqueo es adicional a la sesión autenticada
pendiente para la prueba de campaña. Main local conserva todos los cambios y commits;
no se eliminaron ramas/worktrees ni se reescribió historial.


### Cierre confirmado tras creación autenticada por el usuario

**CAPSTONE-DB-02B CERRADO operativamente.** El usuario comunicó la creación de
`4b5a9626-ddb7-4f48-a93e-b29b8085b349`. La verificación posterior de solo lectura
confirma los diez criterios de cierre operativo de la solicitud. Esta actualización
sustituye el estado parcial y la solicitud pendiente de creación anteriores.

| Elemento | Resultado final |
|---|---|
| Integración | main local, merge `5f12f81`, implementación `63e65da` |
| Función y trigger | Corrección aplicada/verificada; propietario, ACL y trigger conservados |
| Pruebas | 49 PASS, 0 FAIL, 0 SKIP; no repetidas tras cambios exclusivamente documentales |
| Campaña | `4b5a9626-ddb7-4f48-a93e-b29b8085b349` — CAPSTONE-DB-02B — prueba operativa |
| Creación HTTP | POST `/api/campaigns`, 201 Created, 2026-10-12 15:03:58 UTC |
| Readback HTTP | GET `/api/campaigns/4b5a9626-ddb7-4f48-a93e-b29b8085b349`, 200 OK |
| Persistencia | frozen; 1 configuración, 1 miembro pending; expected_count=1 |
| Dataset | `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` |
| Evidencia | `97a466ef-e4bb-4452-b4c3-3a7a87b72dc3` |
| Verificación científica | ml.dataset_verification, success=true, error_code=NULL; verified_requested_splits; train/val solicitados y físicamente verificados |
| Identidad / snapshot | Coincidencia exacta con la evidencia y el contrato |
| Matriz y hashes | Configuraciones y miembros idénticos al contrato; hashes válidos |
| Ejecución científica | 0 runs, 0 attempts; TRAIN/EVALUATE/EXPLAIN no ejecutados |
| Frontend | Flujo autenticado realizado por el usuario; POST/GET confirmados en logs. Sin inspección visual directa del agente |
| Rollback | No requerido |
| Conservación | Campaña mantenida como evidencia; no se crearon campañas adicionales |
| Publicación remota | Sigue bloqueada por revisión automática; pendiente confirmación directa del destino |

Se consultaron `experimental_campaigns`, `campaign_configurations`, `campaign_members`,
`campaign_attempts`, `runs` y `audit_events` usando
`PGOPTIONS='-c default_transaction_read_only=on'` y psql con ON_ERROR_STOP.
Las comparaciones JSONB comprobaron igualdad exacta entre evidencia/snapshot,
contrato/snapshot, matriz/configuraciones y matriz/miembros. Los hashes se recomputaron
con SHA256 de las representaciones canónicas almacenadas. No se escribieron datos.

El evento de aplicación `ml.campaign.configured`, POST `/api/campaigns`, success=true,
con correlation_id `c04c1de6-d00d-4f76-b3f7-d98ee44ff32f` referencia esa campaña.
Los logs de acceso del backend acreditan 201 y GET 200 del ID concreto; el agente no
emitió solicitudes autenticadas ni accedió a tokens. No se atribuye una validación visual.

Evidencia: [campaña y comprobaciones SQL](capstone_db_02b/operational/campaign_evidence.json)
y [respuestas HTTP](capstone_db_02b/operational/campaign_http.txt).
La publicación Git pendiente es una incidencia de entrega separada: no invalida las
comprobaciones de creación, persistencia e integridad de la corrección ya instalada.
