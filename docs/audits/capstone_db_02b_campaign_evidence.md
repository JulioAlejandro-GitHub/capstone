# CAPSTONE-DB-02B — Evidencia del dataset en campañas

Estado documental: `CURRENT_DOC` — corrección técnicamente lista; **aplicación y cierre operativo pendientes de autorización**.

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
