# E10.10.5 — Implementación A y certificación B

**E10.10.5B — RUTA A CERTIFICADA EN POSTGRESQL 17. PENDIENTE DE REVISIÓN Y APROBACIÓN.**

Gate A y B-01 fueron aprobados explícitamente por el usuario. La baseline independiente `pg_v2_baseline` quedó instalada y certificada desde vacío en PostgreSQL 17.9 aislado. **Gate B se solicita; no está autoaprobado.**

## Cambios finales

- B-01: sustitución contractual de roles por capstone_v2_migrator / capstone_v2_runtime en guardas, generador, ACL, manifiesto, provisión, tests, README e inventario. Documentación E10.10.4 afectada: arquitectura, estrategia Alembic y plan de implementación. No se sustituyeron nombres en SQL históricos inmutables.
- env.py: envío sin parámetros de la consulta de identidad que contiene literales LIKE con `%`, compatible con psycopg. No cambió el filtro de seguridad.
- `scripts/db/certify_v2_route_a.py`: descriptor nuevo, preparación exclusiva, preflight persistido, provisión, ejecución Alembic y log de comandos. Directorio seleccionable mediante PGV2_EVIDENCE_DIR; rechazo de sobrescritura/puertos operativos.
- `scripts/db/verify_v2_route_a.py`: comparación de catálogo, render de metadatos del manifiesto, rollback, no-op, backup/restore con identidad por base auxiliar.
- `scripts/db/v2_catalog_probe.py`: lectura nativa de objetos/columnas/tipos/definiciones/owners/ACL/privilegios, sin comparar OID internos entre bases.
- `scripts/db/v2_inject_failure.py`: hook exclusivo del test para fallo SQL real tras 500 DDL; baseline sin switches de fallo.
- `scripts/db/test_v2_route_a_server.py`: fixtures sintéticos y 46 casos de PostgreSQL real como runtime, con rechazo concreto y rollback final.
- Prueba estática adicional B-01 y archivos de auditoría/evidencia actualizados.

[Archivos con hashes finales](e10_10_5b_evidence/run_b01/implementation_files.json), [hashes de recursos](e10_10_5b_evidence/run_b01/resource_hashes.json). La mayoría de estos archivos ya eran no rastreados al comienzo de la sesión; no se interpreta git status como prueba de autoría nueva. No se hicieron commits ni cambios al código operativo.

## Validación y correcciones

**25 tests estáticos / 9 comandos offline / 46 comprobaciones de servidor aprobados.** Instalación Alembic, catálogo sin diferencias, rollback real sin head, repetición sin cambios y backup/restore idénticos. El compilador sólo modifica recursos nuevos de baseline; el instalador no ejecuta el DDL conceptual, SQL históricos ni metadata.create_all(). Sólo sembró el gate técnico. Los datos científicos presentes al cierre son fixtures sintéticos introducidos después de la instalación para probar restore.

Se preservó A-01: external complementario con población/procedencia/protocolo propios, vista separada, exclusión de comparación oficial y calibración VAL. No se modificaron diseño científico, restricciones ni permisos para facilitar pruebas.

Se corrigieron la reserva de nombres por decisión B-01, el defecto del driver en la guarda, fixtures de publicación y el procedimiento de restore. [Detalle y evidencia](e10_10_5_route_a_results.md). La baseline no necesitó correcciones de sintaxis PostgreSQL 17 en sus recursos científicos.

## Documentos de entrega

- [Certificación Ruta A](e10_10_5_route_a_results.md).
- [Diff de catálogo](e10_10_5_catalog_diff.json).
- [Pruebas](e10_10_5_test_results.md).
- [Riesgos y límites](e10_10_5_open_risks.md).
- [Resolución B-01](e10_10_5b_b01_resolution.md).
- [Comandos reales B](e10_10_5b_evidence/run_b01/commands.jsonl) y [validaciones estáticas finales](e10_10_5a_commands.json).

La implementación A y el bloqueo inicial se conservan como historia en [snapshot previo a B-01](e10_10_5b_evidence/b01_original/pre_b01_e10_10_5_implementation.md). Los hashes/roles antiguos de esos snapshots describen aquel momento y no sustituyen el manifiesto vigente.

## Límite de autorización y cierre

PostgreSQL operativo permanece intacto por las acciones de esta entrega: no se conectó por SQL, no fue origen de backup/adopción y no se cambiaron datasets, modelos, usuarios, campañas o eventos reales. Ambos contenedores de prueba quedaron detenidos; los volúmenes y backup aislados se conservan para revisión.

**Se solicita revisión y aprobación explícita de Gate B.** No se inicia C, D ni E, ni adopción legacy ni cutover.
