# CAPSTONE-DB-01 — Inventario PostgreSQL vigente

Estado documental: `HISTORICAL_AUDIT` — observación del 2026-10-12. Fase 1; sin correcciones.

## Fuente primaria e identidad

El inventario proviene de `pg_catalog` del servidor operativo, no de archivos Alembic. Consultas reproducibles: [catalog_queries.sql](catalog_queries.sql), [catalog_supplement.sql](catalog_supplement.sql). Evidencia estructural completa: [catalog_inventory.json](catalog_inventory.json).

| Propiedad | Observado |
|---|---|
| Servicio / contenedor | Compose `db` / `capstone_db`, imagen `postgres:17.9` |
| Host interno / acceso local | `db:5432` / `127.0.0.1:5432` |
| Base | `malaria_experiments` |
| Motor | PostgreSQL 17.9 Debian, aarch64; `server_version_num=170009` |
| Identificador del clúster | `7691366089693499436`, coincide con comentario del volumen Compose |
| Volumen configurado | `capstone_v2_isolated_persistent_data`, externo; no modificado |
| Propietario de la base | `capstone_v2_migrator` |
| Usuario de auditoría/dump | `julio`, superusuario; sesiones SQL y pg_dump con `default_transaction_read_only=on` |
| Usuario efectivo backend | `capstone_v2_runtime`, sin superusuario, BYPASSRLS, CREATEDB, CREATEROLE ni replicación |
| Search path observado | `"$user", public`; esquema resuelto `public` |
| Revisión histórica registrada | `cell_checkpoint_reuse_v2`; no determina validez del esquema |
| Extensiones | `plpgsql` 1.0 en pg_catalog; `pgcrypto` 1.3 en public |

El runtime tiene CONNECT y USAGE de public, pero no CREATE de base/esquema ni TEMP. Migrator tiene CREATE/TEMP y es propietario de objetos; no es superusuario. No se observaron membresías de roles que involucren a los roles capstone. Permisos por tabla/vista, calculados con `has_table_privilege`, constan en el archivo local `diagnostics.jsonl`; ACL estructurales también en `catalog_inventory.json/relations`. Esto describe permisos efectivos observados, no una prueba de escritura.

Backend: `docker-compose.yml:34`, `backend_api/app/config.py:149`, `backend_api/app/db.py:40`. Se verificó la URL efectiva mostrando únicamente host/base/usuario. Scripts ML: `persistence/database.py:54` carga entorno y valida destino. El launcher local `execution/local_launch.py:50` obtiene base y clave runtime del `.env` raíz y construye destino loopback; `bootstrap` activa `CAPSTONE_LOCAL_TRAIN=1`. No se imprimieron secretos. Scripts administrativos pueden tener otros roles/destinos: sus configuraciones no certifican que se hayan ejecutado.

## Cobertura estructural

| Objeto | Cantidad / detalle |
|---|---|
| Esquemas de aplicación | 1: public, propietario pg_database_owner |
| Esquemas internos observados | pg_catalog, information_schema, pg_toast; pg_temp_13/16 y pg_toast_temp_13/16 |
| Tablas | 105, incluida alembic_version; 104 restantes |
| Vistas | 33; cero materializadas |
| Columnas de tablas | 1.515; total con vistas 2.280 |
| PK / FK / UNIQUE | 105 / 254 / 77 |
| CHECK / constraint triggers | 521 / 10 |
| Índices | 416; todos válidos en catálogo |
| Secuencias | 1; definición y dependencia en anexos |
| Funciones de aplicación | 80 |
| Funciones de extensión en public | 36, propiedad de pgcrypto; no deben recrearse aisladamente de la extensión |
| Procedimientos | 0 en esquemas no internos |
| Triggers de aplicación / internos | 107 / 1.016; todos habilitados `O` |
| Dependencias exportadas | 5.906 filas; incluye reglas de vistas, constraints y funciones |
| Constraints sin validar | 0 |
| RLS / policies de public | Sin policies; consultar flags por relación |
| Dominios/enums/rangos de aplicación | 0 |
| Tablas particionadas / servidores externos / large objects | 0 / 0 / 0 |

`pg_depend` no registra necesariamente referencias SQL dinámicas o nombres contenidos en cuerpos PL/pgSQL. Por ello se conservan definiciones completas y se complementan con lectura del código; una ausencia de dependencia en ese catálogo no prueba que un objeto esté sin uso.

Anexos completos:

- [Tablas, columnas y relaciones por tabla](table_inventory.md).
- [Columnas con tipos, nullability, defaults, identity y generated](columns.csv).
- [Constraints y clasificación](constraints_classification.csv).
- [Índices: método, unicidad y definición](indexes.csv).
- [Secuencias](sequences.csv), [vistas y definiciones](views.csv), [dependencias](dependencies.csv).
- [Funciones: firma, lenguaje, cuerpo y consumidores trigger](routines_classification.csv).
- [Triggers, internos y de aplicación](triggers_classification.csv).

Núcleos identificados: `experimental_campaigns/campaign_members/campaign_attempts`; `runs/train_execution_sessions/train_execution_records`; `run_configurations/evaluations/run_clinical_metrics`; `assessment_identities/assessment_attempts/assessment_results/assessment_artifacts`; `xai_*`; datasets/materializaciones/asignaciones; `research_subjects/scientific_cases/blood_samples/smear_slides/microscopy_images`; detecciones, crops, clasificaciones, explicaciones celulares y revisión científica. La jerarquía y las acciones de cada FK están explicitadas en los anexos.

## Respaldo y alcance de recuperación

Carpeta local excluida de Git: `backups/capstone_db_01/20261012_audit/`. Directorio 0700 y archivos 0600. La regla existente `backups/` se verificó con `git check-ignore`; no se cambiaron configuraciones.

| Archivo | Contenido |
|---|---|
| postgresql_full.dump | pg_dump custom completo, estructura y datos; 34.025.630 bytes |
| postgresql_schema.sql | SQL sin datos: tablas, índices, constraints, secuencias, vistas, funciones, triggers y ACL |
| functions.sql | Definiciones completas de funciones de aplicación/extensión en esquemas no internos; cero procedimientos |
| triggers.sql | Definiciones completas de los 107 triggers de aplicación |
| constraints.json / dependencies.json | Constraints asociados y dependencias del catálogo |
| catalog.json / restore_list.txt | Catálogo fuente y tabla de contenido del dump |
| backup_manifest.json | Tamaños, SHA-256, versiones, resultados y límites de verificación |

Ambos dumps terminaron con código 0; listado y decodificación completa mediante `pg_restore --file=/dev/null` terminaron con código 0. Se contrastaron objetos del catálogo, se comprobaron archivos no vacíos y se recalcularon los hashes. La comprobación final más estricta consta en `backup_verification.json`.

No se efectuó una restauración: no se certifica una recuperación ensayada. `pg_dump` no incluye roles globales, configuración del servidor ni archivos externos (checkpoints/imágenes). Recuperar la base con propietarios/ACL exige disponer de los roles y extensiones; recuperar el sistema completo exige además sus artefactos. No se exportaron contraseñas de roles. Cada dump/catálogo usa su propia instantánea de solo lectura; no constituyen una instantánea distribuida con el almacenamiento externo.

Comprobaciones documentales y huella del manifiesto: [artifact_checks.json](artifact_checks.json). Huellas SHA-256 de fuentes inspeccionadas para reproducir referencias: [source_fingerprints.json](source_fingerprints.json). Resumen de clasificación: [classification_summary.json](classification_summary.json).
