# Evidencia del inventario B.3C.2

Reportes documentales, no manifiestos ni entradas para ejecutar una purga. Los UUID son referencias técnicas; no se exportan nombres de pacientes, payloads de auditoría, credenciales ni binarios.

- table_counts.csv: resumen por tabla y criterio.
- clinical_ids.csv: una fila por PK objetivo, en orden determinista.
- clinical_storage_keys.csv: una fila por referencia clínica y metadata esperada.
- fingerprints.csv: fingerprint del conjunto por tabla.
- preservation_checks.csv: todas las verificaciones y sus estados.
- audit_classification.csv: IDs exactos, categoría y fingerprint por evento, incluidos preservados.
- purge_blocking_triggers.csv: protecciones que requieren resolver el contrato de purga.
- legacy_references.csv: inventario por coincidencia textual y construcción segmentada.
- legacy_local_files.csv: metadata y clasificación de todos los archivos legacy locales.
- legacy_tracked_files.csv: subconjunto rastreado por Git.
- legacy_database_references.csv: coincidencias exactas de keys/rutas en PostgreSQL (sin audit_events; auditoría se trata separadamente).

La ejecución usó exclusivamente DATABASE_URL desde backend, BEGIN / READ ONLY, statement_timeout 30s, lock_timeout 5s y ROLLBACK. El SQL principal contiene todo lo necesario para regenerar los reportes clínicos; las búsquedas del linaje están en un segundo SQL. El informe principal detalla fuentes, límites y consumidores.
