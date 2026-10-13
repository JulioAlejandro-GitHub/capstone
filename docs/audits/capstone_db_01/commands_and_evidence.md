# CAPSTONE-DB-01 — Bitácora de comandos y evidencia

Estado documental: `HISTORICAL_AUDIT` — 2026-10-12. Registro de operaciones realizadas, sin secretos.

Directorio de trabajo: raíz del repositorio. `B` en esta bitácora abrevia `backups/capstone_db_01/20261012_audit/`; no es una variable de conexión. No ejecutar SQL del dump contra producción.

| Operación ejecutada | Resultado / evidencia |
|---|---|
| cat del adjunto del usuario y SKILL.md aplicables | Restricciones de Fase 1 identificadas; prioridad a solicitud explícita de cobertura completa |
| git status --short inicial | Sin cambios preexistentes |
| rg --files -g AGENTS.md | Sin archivos coincidentes; código 1 |
| command -v docker psql pg_dump pg_restore | Herramientas existentes; no instalaciones |
| docker ps --format nombre/imagen/puertos | Primer intento bloqueado por sandbox; repetido con escalación autorizada, identifica tres contenedores |
| docker exec capstone_db ... psql -X -At -c SELECT identidad | malaria_experiments, julio, 17.9, search_path, transaction_read_only=on |
| git check-ignore B/postgresql_full.dump | Regla backups/ efectiva |
| umask 077; mkdir carpeta nueva; chmod 600 archivos | Respaldo privado; comprobación final 0700/0600 |
| docker exec ... pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom > B/postgresql_full.dump | Código 0, 34.025.630 bytes; variables resueltas dentro del contenedor, sin imprimir claves |
| docker exec ... pg_dump ... --schema-only > B/postgresql_schema.sql | Código 0 |
| pg_restore --list B/postgresql_full.dump > B/restore_list.txt | Código 0, tabla de contenido legible |
| pg_restore --file=/dev/null B/postgresql_full.dump | Código 0; decodificación completa sin conexión ni restauración |
| psql -X -qAt < catalog_queries.sql | Código 0, B/catalog.json; BEGIN READ ONLY y ON_ERROR_STOP |
| Exportación local desde catalog.json | functions.sql, triggers.sql, constraints.json, dependencies.json; inventarios documentales |
| psql ... < diagnostic_queries.sql | Código 0; E10 capacidades y contrato v2, conteos, permisos; B/diagnostics.jsonl |
| psql ... < assessment_queries.sql | Código 0; estados agregados/evidencias y reproducción literal de CTE del reporte; B/assessments.jsonl |
| psql ... < catalog_supplement.sql | Código 0; clúster, tipos y permisos; B/catalog_supplement.jsonl |
| psql ... < explain_relationship_queries.sql | Código 0; dos identidades Grad-CAM, sin referencia explícita EVALUATE; B/explain_relationships.jsonl |
| docker logs --tail 15000 backend/db; segundo pase --timestamps | Captura en memoria; se guardaron solo firmas permitidas y fechas/contexto, no logs brutos ni parámetros |
| docker exec backend python: inspección os.environ mediante urlparse | host db, puerto 5432, base malaria_experiments, rol capstone_v2_runtime; sin contraseña |
| docker exec backend python: require_e10_schema / require_v2_capabilities | Conexión con default_transaction_read_only=on; E10 rechaza revisión, v2 PASS; sin reserva/claim |
| docker exec backend python -B: list_training_summaries y get_training_lineage_children | Funciones inspeccionadas de solo lectura; 14 TRAIN, un EVALUATE, cero EXPLAIN; sin truncamiento |
| rg de términos solicitados y git ls-files + lectura/AST local | code_search_inventory.csv; search_coverage.json; cobertura de todos los proyectos, sin ejecutar módulos |
| psql ... < catalog_queries.sql al cierre | B/catalog_final.json; mismos objetos/definiciones/permisos/revisión que al inicio |
| pg_restore --schema-only --file B/schema_from_custom.sql B/postgresql_full.dump | Código 0; estructura igual al SQL separado al omitir comentarios y tokens restrict aleatorios |
| Python hashlib.sha256 sobre archivos locales | Hashes del manifiesto; recalculados después de producir evidencia final |
| git diff --check; git status; verificación git check-ignore y modos | Verificación documental y exclusión de respaldos al cierre |

Todas las invocaciones psql/pg_dump usaron `PGOPTIONS='-c default_transaction_read_only=on'`. Consultas SQL reproducibles se adjuntan completas; inspecciones Python usaron librerías existentes. No se invocaron funciones SQL que muten datos: los cuerpos de funciones/triggers se leyeron como texto de catálogo.

Búsquedas exploratorias con rutas inexistentes (`frontend/src/api`, algunos nombres tentativos de módulo) devolvieron código 2; se resolvieron buscando nombres reales. Una ruta inicial `/app/backend_api/app/repositories/assessment_lineage.py` no existía en el contenedor; se comprobó después `/app/app/repositories/assessment_lineage.py` y su SHA-256. Estos resultados no se trataron como ausencia funcional del componente.

Los generadores temporales de inventario solo leyeron archivos y escribieron documentación/evidencia. No hay framework de auditoría instalado, servicios añadidos ni cambios al código operativo. La lectura del catálogo inicial/final acredita igualdad estructural; no equivale a una huella de todos los datos durante actividad concurrente. La ausencia de escrituras de esta auditoría se sustenta en comandos y transacciones de solo lectura.

## Aclaración posterior del usuario sobre DB-01

El usuario precisó el literal CAMPAIGN_DATABASE_OPERATION_FAILED. Se actualizaron análisis, dependencias, propuesta y cierre para retirar la hipótesis de red del caso observado y distinguir el código público genérico de la excepción interna. Solo se editaron documentos; no hubo nuevas consultas a PostgreSQL, respaldos ni modificaciones funcionales.
