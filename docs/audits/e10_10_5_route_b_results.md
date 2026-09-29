## Actualización E10.10.5D.1 — decisión estructural pendiente

**E10.10.5D — BLOQUEADA. GATE D NO APROBABLE.** D-01 demostrado: legacy es GENERATED ALWAYS AS IDENTITY; baseline omite generación (INSERT sin id falla 23502) y acepta IDs explícitos que legacy rechaza (428C9). D-02 comprende 41 representaciones divergentes: 39 columnas retenidas resuelven a otra función; dos tablas son MERGE aprobado. Legacy usa pg_catalog.gen_random_uuid y baseline el wrapper de pgcrypto, con dependencias y permisos distintos. Prueba auxiliar: revocar EXECUTE del wrapper mantiene INSERT legacy y rechaza baseline con 42501.

La Parte 2 exige detenerse ante falta de equivalencia. No se modificaron baseline/manifiesto/adaptador/comparador. Se propone conservar IDENTITY y fijar explícitamente el binding pg_catalog de las 39 columnas; requiere decisión antes de cambiar esquema. La certificación B es anterior a esta propuesta y no acredita una corrección. Preservación de la copia D original: 97/97 conteos/hashes y secuencia intactos; cero conexiones operativas. Solo probes en auxiliares aisladas. Preflight/adopción/recertificación/rollback/repetición/restore siguen pendientes. No E ni cutover.

[Diagnóstico, decisión, pruebas y comandos](e10_10_5d_structural_resolution.md), [inventario exacto de defaults](e10_10_5d1_evidence/default_inventory.json), [preservación](e10_10_5d1_evidence/preservation.json).

---

# E10.10.5D — Informe de etapa

**E10.10.5D — BLOQUEADA. GATE D NO APROBABLE.**

## 1. Objetivo y autorización
Gate C aprobado expresamente por el usuario. Se inició exclusivamente D para certificar adopción sobre copia aislada. No se inició E ni cutover. No se eludió ninguna guarda.

## 2. Origen y copia consistente
PostgreSQL operativo 17.9, base `malaria_experiments`, OID 1600436, system identifier `7668020338728398886`, revisión observada `20260922_01`. Acceso SQL mediante SELECT y transacciones READ ONLY; pg_dump custom 17.9 con `default_transaction_read_only=on` y lock timeout 5 s. Sin DDL/DML/Alembic/stamp, cambios de roles ni detención de procesos operativos.
Backup de 12518509 bytes, SHA-256 `fa50d1dedb10e2a04aa99125143f2b74c213eceb679db1e69ffc1d9a882b71f6`. Ubicación privada en [recibo](e10_10_5d_evidence/source_backup.json); permisos 0600/directorio 0700 fuera del repositorio. pg_dump obtiene su propio snapshot consistente; las consultas preliminares son snapshots separados y no se presentan como el mismo snapshot.

## 3. Aislamiento e identidad del destino
Contenedor `09aeb81b36210177134e73c1d735967f2d053e6d4fb8723e3783a14a43787cc3`, volumen/base `capstone_v2_isolated_8c5114865703`, puerto `127.0.0.1:55479`, cluster `7691066755790737451`, OID 16386, PostgreSQL 170009. Credenciales aleatorias independientes; roles v2 sin privilegios administrativos. Identidad y guardas Docker comprobadas antes de provisión/restauración. Se restauró con `--no-owner --no-acl --role=capstone_v2_migrator --single-transaction --exit-on-error`; esa preparación de ownership/ACL es explícita, no una equivalencia con el origen. Ningún recurso operativo se montó en el destino.
Backup adicional de la copia legacy restaurada: SHA-256 `c197888c05358e2c28e8b5c80c7a7ec01751b8548eb9b2c56918d5af3cd6e281`. Destino detenido al cierre; volumen y backups conservados. [Identidad](e10_10_5d_evidence/isolated_identity.json), [estado final](e10_10_5d_evidence/final_state.json).

## 4. Preflight obligatorio
Origen: revisión correcta; 22 checksums iguales al contrato y a los archivos históricos; inventario exacto de 97 tablas; siete grupos de esquema iguales al contrato. Gate libre y evidencia vacía; cero filas de campañas/sesiones/intentos/jobs/runs. Dos conexiones cliente ajenas inactivas observadas, ninguna detenida. Tres modelos, un usuario, dos datasets y una versión de dataset. Se preservó la evidencia registrada sin leer ni modificar archivos científicos.
Copia: 97 conteos coinciden con la observación de origen; hashes canónicos de cada tabla registrados en [inventario](e10_10_5d_evidence/reference_inventory.json). Esto no acredita equivalencia de hashes origen/restore bajo un snapshot compartido. Revisión legacy conservada. El preflight de captura falló en secuencia; preflight completo, integridad referencial y contratos científicos finales **no certificados**.

## 5. Transformaciones y bloqueo
**D-01: `LEGACY_SEQUENCE_DRIFT`.** La secuencia `experiment_execution_events_id_seq` usa dependencia interna `i` de IDENTITY; Ruta A exige dependencia automática `a`. Nombre, parámetros, tabla y columna enlazada coinciden; estado `last_value=1`, `is_called=false`. No es un OID variable ni se eliminó de la comparación. [Diff exacto](e10_10_5d_evidence/sequence_difference.json).
No se invocó `apply`, no se ejecutó delta ni transición de head. No se cambió la secuencia para satisfacer la guarda. Resolver compatibilidad entre identidad legacy, baseline y preparación requiere revisión explícita antes de reanudar D.
Diagnóstico secundario: `LEGACY_SCHEMA_DRIFT` por defaults cualificados, incluidos `pg_catalog.gen_random_uuid()`. [Diff sin normalizar](e10_10_5d_evidence/restored_schema_diff.json). La representación puede depender del search_path y de la resolución de funciones; no se certificó equivalencia ni se clasificó como corrupción científica.

## 6. Certificación y pruebas aisladas
Backup consistente: ejecutado, salida 0. Restore legacy: ejecutado, salida 0. Guardas: bloqueo real antes de adopción. Conteos legacy: 97/97 coinciden; hashes destino registrados. Adopción completa, comparación final con Ruta A, rollback intermedio, repetición, backup/restore adoptado y reconciliación post-restore: **NO EJECUTADOS por bloqueo**. No existe estado parcialmente adoptado porque no comenzó la transformación; esto no sustituye un ensayo de rollback.
Usuarios/modelos/dataset tienen conteos de referencia, no certificado final. E10, evaluaciones externas, calibración y publicación están vacíos: no se inventaron fixtures como evidencia histórica ni se declara probada preservación de historial poblado.

## 7. Evidencia y reproducción
[Comandos Docker y códigos](e10_10_5d_evidence/commands.jsonl), SQL de solo lectura `source_readonly_precheck.sql`, `source_inventory.sql`, `source_schema.sql`, [bloqueo](e10_10_5d_evidence/blocker.json), [equivalencia](e10_10_5_data_equivalence.json). Runner `scripts/db/certify_v2_route_b.py`; diagnóstico `scripts/db/inspect_v2_route_b_block.py`. El runner rechaza reutilizar evidencia existente; no reejecutar mientras D esté bloqueada.
Comando efectivo: `PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python scripts/db/certify_v2_route_b.py` → 1 (`LEGACY_SEQUENCE_DRIFT`). Diagnóstico readonly → 0, tras un primer diagnóstico → 1 (`LEGACY_SCHEMA_DRIFT`). Dependencias: pglast 8.4 instalado únicamente en /private/tmp para Python 3.12. Dos intentos iniciales de importación fallaron antes del backup (pglast ausente / ABI de Python incompatible); no fueron ensayos PostgreSQL. El primer parser del resultado JSON también falló por salida multilínea y se corrigió sin repetir escrituras. Sin credenciales ni filas privadas en informes.

## 8. Riesgos y recuperación
D-01 impide certificar adopción; diferencias de defaults requieren diagnóstico. No se modifica baseline ni adaptador automáticamente. Backups contienen información privada y permanecen fuera de Git; /private/tmp requiere conservación para continuidad del ensayo. Recuperación disponible: restaurar source.dump en **otro** clúster/volumen/puerto aislado con identidad comprobada, roles v2 propios y el pg_restore registrado; nunca sobre origen. El restore legacy ya se ensayó; no existe un backup adoptado. No afirmar pérdida de datos por esta diferencia estructural.

## 9. Cierre y Gate D
**E10.10.5D — BLOQUEADA. GATE D NO APROBABLE.** Se solicita revisión explícita de los bloqueos. La aprobación de Gate D debe quedar pendiente hasta resolverlos y completar todas las pruebas obligatorias; no corresponde solicitar aprobación de una adopción no certificada. No se inicia E automáticamente y no se ejecuta cutover.
