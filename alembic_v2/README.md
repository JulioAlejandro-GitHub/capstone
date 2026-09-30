# Estado vigente — DBV2.2 + corrección aprobada R1

Baseline independiente `pg_v2_baseline`, `down_revision=None`, un root y un head. Materializa DBV2.1 corregido: 104 tablas de aplicación + `alembic_version`, 33 views, 251 FK, 518 CHECK, 77 UNIQUE, 413 índices de aplicación, 79 funciones propias y 105 triggers. No crea `schema_migrations` ni `model_governance_backfill_audit`.

[Certificación DBV2.2](../docs/audits/db_v2/dbv2_2/restart_r1/dbv2_2_baseline_report.md), [resolución R1](../docs/audits/db_v2/dbv2_2/dbv2_2_r1_xai_trigger_resolution.md) y [bloqueo original conservado](../docs/audits/db_v2/dbv2_2/dbv2_2_baseline_report.md). Pendiente GATE DBV2.2; no freeze final, transferencia, cutover ni inicio de SW-v2.

`clinical_target_recall numeric NOT NULL`, sin DEFAULT, CHECK `0 < clinical_target_recall AND clinical_target_recall <= 1`. Las nueve tablas XAI y el overlay E-04 se verifican por identidad y definición, además de los conteos.

## Instalación actual

Preparar únicamente un PostgreSQL 17.9 desechable con roles `capstone_v2_migrator` / `capstone_v2_runtime`, descriptor de aislamiento verificado y URL explícita. No cargar `.env`. `PGV2_TARGET` apunta al descriptor autorizado DBV2.2 (`gate_dbv21_approved=true`); `PGV2_DATABASE_URL` debe coincidir exactamente con él.

```sh
alembic -c alembic_v2.ini upgrade head
alembic -c alembic_v2.ini current
alembic -c alembic_v2.ini heads
```

También se admite `-x target=<descriptor>`. El runtime sólo puede leer `alembic_version`; no tiene DDL, TEMP, TRUNCATE ni escritura del ledger. El instalador verifica recursos/identidad antes de escribir y no depende de historia legacy, adoption o stamp.

## Construcción y verificación estáticas actuales

Con pglast 8.4 disponible para el intérprete elegido:

```sh
python3 scripts/db/validate_dbv2_1.py --reference-root docs/audits/db_v2/dbv2_2/restart_r1/reference_candidate
python3 scripts/db/build_dbv22_baseline.py
python3 scripts/db/validate_v2_static.py
```

`build_dbv22_baseline.py --write` reconstruye recursos exclusivamente en desarrollo, antes del freeze. La lectura del SQL de diseño es offline: no se ejecuta ese archivo. La revisión instalada sólo consume los recursos propios en `baseline/`. Las copias `reference_candidate` sirven para comparar con la candidata histórica y verificar sus hashes originales; no son dependencias ejecutables del instalador.

## Reproducir certificación en otro entorno nuevo

Seleccionar un directorio de evidencia nuevo y un puerto libre dedicado mediante `DBV22_EVIDENCE_DIR` y `DBV22_PORT`; nunca reutilizar un target. El runner utiliza el socket local Docker Desktop de esta estación, que debe configurarse y verificarse al trasladarlo a otra estación. Necesita la imagen local `postgres:17.9` y las dependencias de Alembic/psycopg.

```sh
python scripts/db/certify_dbv22.py provision
python scripts/db/certify_dbv22.py upgrade
python scripts/db/certify_dbv22.py catalog
python scripts/db/test_dbv22_server.py
python scripts/db/test_dbv22_e04.py
python scripts/db/verify_dbv22.py compare
python scripts/db/verify_dbv22.py repeat
python scripts/db/verify_dbv22.py failure
python scripts/db/verify_dbv22.py restore
```

El restore se autentica como migrador para conservar ownership de pgcrypto y repone explícitamente la ACL de base, omitida por `pg_dump` sin `--create`. Los únicos datos del backup son el head Alembic y el singleton técnico. Los fixtures se revierten. Las suites estáticas se documentan con sus intérpretes y resultados en la evidencia; el parser PostgreSQL 18.4 no sustituye al servidor 17.9.

---

# Historial anterior a DBV2.1 (referencia, no instrucciones vigentes)

# Estado histórico — E10.10.5E.4

Baseline E-04 recertificada en PostgreSQL 17.9: [resolución](../docs/audits/e10_10_5e4_resolution.md) y [certificado](../docs/audits/e10_10_5e4_evidence/route_a/certificate.json). Integra E-03/E-04 y conserva D-01 a D-06/E-01/E-02. La integración permanece detenida por [E-05](../docs/audits/e10_10_5e5_decision.md); Gate E bloqueado. Los estados de certificación siguientes son históricos.

> Estado D.3: D-04 resuelta y preflight aprobado. La aplicación se revirtió por FINAL_CATALOG_MISMATCH: D-05 (columna structural_hash generada ausente del contrato objetivo) y D-06 (cuatro CHECK pendientes de equivalencia). Baseline/certificado D-03 no modificados en D.3. Véase docs/audits/e10_10_5_route_b_results.md. Los estados anteriores de este documento son históricos.

# Revisión arquitectónica D-03 (E10.10.5D.2)

Baseline corregida y recertificada en PostgreSQL 17.9. El generador aplica el contrato explícito [d03_contract.json](d03_contract.json) sobre la especificación conceptual anterior: conserva `GENERATED ALWAYS AS IDENTITY` en `experiment_execution_events.id`, suprime la secuencia manual redundante y cualifica únicamente los 39 defaults UUID autorizados con `pg_catalog`. Las entidades nuevas y las dos tablas MERGE no reciben sustituciones globales. El manifiesto fija el hash de esta decisión, identidad y parámetros de secuencia. El catálogo compara además funciones resueltas y dependencias de defaults.

[Certificación histórica D-03](../docs/audits/e10_10_5_route_a_results.md). La certificación B anterior solo corresponde al manifiesto previo y se conserva en `docs/audits/e10_10_5b_evidence/`. El preflight de adopción D sigue bloqueado por D-04 (ownership de funciones de extensión); esta certificación no autoriza E ni cutover.

## Documentación original de instalación

# PostgreSQL v2 — baseline independiente y certificación Ruta A

**E10.10.5B — RUTA A CERTIFICADA EN POSTGRESQL 17. PENDIENTE DE REVISIÓN Y APROBACIÓN.**

Raíz `pg_v2_baseline`, `down_revision=None`, seleccionada exclusivamente mediante `alembic_v2.ini`. Gate A y B-01 fueron aprobados por el usuario; Gate B requiere revisión. [Resultados, identidad y evidencia](../docs/audits/e10_10_5_route_a_results.md).

## Contrato vigente B-01

- Migrador/owner: `capstone_v2_migrator`.
- Runtime independiente: `capstone_v2_runtime`.
- Ninguno tiene SUPERUSER, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS ni memberships.
- El runtime tiene DML contractual bajo restricciones/triggers; no DDL, TEMP, TRUNCATE, edición del ledger de migraciones ni escritura de alembic_version. Las protecciones append-only permanecen activas.
- Sólo el administrador de la instancia aislada prepara roles/base y concede al migrador EXECUTE de `pg_catalog.pg_control_system()` para acreditar identidad. La revisión no crea roles.

La [decisión B-01](../docs/audits/e10_10_5b_b01_resolution.md) conserva los nombres anteriores y el rechazo PostgreSQL. No se modificaron SQL históricos inmutables.

## Instalación y guardas

El instalador consume únicamente recursos propios versionados de `baseline/`; verifica checksums de archivos/sentencias antes de escribir. No importa la aplicación, no carga `.env`, no ejecuta SQL históricos, DDL conceptual ni `Base.metadata.create_all()`. `alembic.ini` y el árbol Alembic operativo permanecen intactos.

Las fases son: settings/extensión, secuencia, 102 tablas de aplicación, funciones, claves/índices UNIQUE, CHECK/FK, índices restantes, vistas, triggers, owners/ACL y gate técnico libre. Alembic administra su propia tabla número 103. No se siembran datos científicos ni registros históricos. `check_function_bodies=true` permanece activo.

`env.py` exige transacción, advisory lock y destino explícito. Rechaza stamp, downgrade, offline installer, conexiones externas, esquemas adicionales y bases legacy/parciales/ambiguas. La consulta de esquemas usa `no_parameters=True` para conservar los literales `%` con psycopg. La guarda de repetición comprueba relaciones/head; la certificación exhaustiva es una comprobación separada.

El descriptor exige aprobación de A para B, UUID/etiquetas Docker, ID completo del contenedor, volumen local exclusivo sin bind/NFS ni montajes compartidos, PGDATA exacto, contenedor no privilegiado y puerto propio publicado sólo en 127.0.0.1, distinto de 5432/5433. La guarda del servidor exige PostgreSQL 17, system_identifier, OID/nombre de base, owner/usuario/sesión correctos, roles limitados y ausencia de recuperación.

La URL procede sólo de `PGV2_DATABASE_URL`, driver `postgresql+psycopg`, host/puerto/base/usuario exactos, sin opciones que redirijan. Se selecciona el descriptor mediante `-x target=<archivo>`. El descriptor parcial del bloqueo original no es una autorización válida; el destino B-01 usa uno nuevo y completo.

## Reproducción estática

Dependencias: `requirements.txt`, `requirements-static.txt` y ruff. Comando usado en esta estación:

```sh
PYTHONPATH=/tmp/e10_10_4_sql_parser:. python3 scripts/db/check_v2_stage_a.py --alembic-python malaria_dl_local_project/.venv/bin/python
```

El parser local es pglast 8.4 / PostgreSQL 18.4. Las 25 pruebas estáticas no sustituyen las pruebas PostgreSQL 17.9. Los recursos se regeneran con `build_v2_baseline.py --write`; `--check` prueba reproducción determinista. Sólo `10_privileges.sql` cambió por B-01.

## Reproducción PostgreSQL aislada

Requiere autorización explícita de B, Docker local e imagen `postgres:17.9`, un puerto libre exclusivo y un directorio nuevo de evidencia. Nunca reutilizar un descriptor parcial o uno de otra instancia. Ejemplo de preparación **para una ejecución nueva autorizada**:

```sh
export PGV2_EVIDENCE_DIR=docs/audits/e10_10_5b_evidence/new_authorized_run
python3 scripts/db/certify_v2_route_a.py init 55477
python3 scripts/db/certify_v2_route_a.py setup
malaria_dl_local_project/.venv/bin/python scripts/db/certify_v2_route_a.py preflight
python3 scripts/db/certify_v2_route_a.py upgrade
malaria_dl_local_project/.venv/bin/python scripts/db/verify_v2_route_a.py catalog
malaria_dl_local_project/.venv/bin/python scripts/db/test_v2_route_a_server.py
malaria_dl_local_project/.venv/bin/python scripts/db/verify_v2_route_a.py rollback
malaria_dl_local_project/.venv/bin/python scripts/db/verify_v2_route_a.py idempotence
malaria_dl_local_project/.venv/bin/python scripts/db/verify_v2_route_a.py backup_restore
```

El runner fija el socket Unix local Docker Desktop de la estación certificada; en otra estación debe configurarse explícitamente el endpoint local y acreditarse con las mismas guardas. No usa Docker remoto ni credenciales operativas. La prueba usa trust sólo en el clúster desechable local; se detuvo el contenedor al terminar y se conservaron volumen/backup para revisión.

El comparador representa el manifiesto canónicamente en PostgreSQL 17 dentro de una base auxiliar vacía/transacción revertida y contrasta también las declaraciones de columnas del manifiesto. El fallo intermedio se inyecta desde un hook de prueba separado, después de 500 DDL reales, sin modificar la baseline. El restore usa `--role capstone_v2_migrator` y reproduce ACL de base y el REVOKE explícito Alembic que pg_dump no conserva en esa representación; se comprueban catálogo completo, datos y secuencia.

## Límites

No se implementó adopción C ni reconciliación D ni adaptación de writers/servicios/UI E. El runtime legacy mantiene sus guardas y no se declaró compatible con el head v2. La exclusión externa y calibración VAL se ensayaron en el esquema; los recorridos de aplicación completos siguen fuera de B. Ningún resultado autoriza cutover ni escrituras operativas. El trabajo se detiene para solicitar Gate B.
