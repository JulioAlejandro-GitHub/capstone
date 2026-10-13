# CAPSTONE-DB-01 — Cierre de Fase 1

Estado documental: `HISTORICAL_AUDIT` — 2026-10-12. Auditoría y respaldo; Fase 2 no iniciada.

**Estado final: NO APROBABLE para una limpieza general de restricciones.** El respaldo y el inventario crítico están verificados. Se identificaron defectos concretos suficientes para revisar una Fase 2 acotada, pero queda clasificación semántica pendiente y falta atribuir inequívocamente el código genérico de DB-01 a la excepción interna de esa solicitud. Este estado no implica fallo del dump ni invalidez del esquema PostgreSQL.

| Resultado solicitado | Estado |
|---|---|
| Instancia operativa correcta | Identificada: capstone_db / malaria_experiments / PostgreSQL 17.9 |
| Respaldo PostgreSQL completo | **PASS** |
| Respaldo estructural | **PASS** |
| Inventario de funciones y triggers | **PASS**: 80 funciones de aplicación, 36 de extensión y 107 triggers de aplicación; 0 procedimientos |
| Inventario crítico | **PASS**: 105 tablas, 33 vistas, 967 constraints, 416 índices, 1 secuencia; anexos completos |
| Clasificación de restricciones | **PARCIAL**: estructural completa; clasificación conservadora y D para semántica no demostrada |
| DB-01 | Incompatibilidad de evidencia identificada; CAMPAIGN_DATABASE_OPERATION_FAILED es el código genérico del repositorio, pendiente de correlación con la excepción interna concreta |
| DB-02 | Causa identificada y reproducida en solo lectura: revisión histórica exigida pese a capacidades E10/v2 válidas |
| DB-03 | Causa identificada: SQL/DTO excluyen assessments EXPLAIN E6; persistencia verificada mediante conteos |
| Dependencias históricas | Identificadas las principales activas; índice transversal y pendientes separados |
| Integridad PostgreSQL | **Sin modificaciones por esta auditoría**; catálogo inicial/final y revisión histórica iguales |
| Código/configuración funcional | Sin modificaciones; no migraciones, reinicios ni pipelines |

## Respaldo verificable

Carpeta local: `backups/capstone_db_01/20261012_audit/`. Manifiesto: `backup_manifest.json`; detalle de verificación: `backup_verification.json`. Directorio 0700, archivos 0600, exclusión Git comprobada.

Los dos pg_dump finalizaron con código 0. Se verificaron lectura del TOC, decodificación completa sin restaurar, entradas TABLE DATA de las 105 tablas y coincidencia estructural entre SQL separado y estructura decodificada del custom. Hash normalizado común de estructura: `df4d37a3ae56d80dc5facf131ac15e9a9baebbb8d2475a3c9d1cdf6e39e45729`. Los hashes binarios exactos, tamaños y fecha UTC están en el manifiesto.

No hubo restauración de prueba. Los roles globales y artefactos externos no forman parte del dump de base. No se afirma recuperación integral del sistema ni invariancia global de datos frente a otros procesos concurrentes.

## Hallazgos confirmados

- La única fila alembic_version es `cell_checkpoint_reuse_v2`; la whitelist runtime solo acepta `20260922_01`/`pg_v2_baseline`. El contrato instalado pasa las verificaciones E10 y v2. Existen ramas adicionales de persistencia/lectura condicionadas por el nombre de revisión.
- campaign_guard exige evidencia `verified`; la creación actual verifica train/val y produce `verified_requested_splits`. Hay evidencia persistida y errores en logs coherentes con el rechazo. El guard también protege identidad y matriz científica: no debe eliminarse en bloque.
- Dos EXPLAIN Grad-CAM verificados tienen 5.386 resultados y 10.772 referencias a artefactos en assessments, con TRAIN válido. La lectura del backend devuelve cero EXPLAIN porque solo proyecta EVALUATE E6 y EXPLAIN basado en runs. No es truncamiento ni ausencia de resultados persistidos.
- Todas las constraints están validadas; todos los índices están válidos y los 1.123 triggers están habilitados. Esto acredita flags de catálogo, no sustituye una comprobación fila por fila de todas las invariantes históricas.

## Incertidumbres y riesgos

El usuario corrigió el mensaje DB-01 a CAMPAIGN_DATABASE_OPERATION_FAILED. Su generación está explicada por el código; no hay un fallo de red demostrado. La atribución del error genérico a un rechazo específico requiere correlación con logs. Reglas de transición de campañas, ejecución controlada y admisión legacy contienen política mezclada con integridad; no se demostró que todas sean prescindibles. La clasificación por dominio de CHECK no reemplaza revisión individual de sus constantes. Referencias PL/pgSQL dinámicas pueden no figurar en pg_depend. Los artefactos externos no se verificaron por contenido. El barrido de todo el código está indexado, pero no constituye prueba de ejecución de cada consulta o script.

Eliminar solo la whitelist puede activar rutas antiguas de persistencia. Eliminar triggers por nombre puede romper identidad clínica, separación TEST o atomicidad. Crear runs sintéticos para mostrar EXPLAIN duplicaría identidad científica. Estos riesgos motivan la propuesta acotada y el estado no aprobable para limpieza general.

## Recomendación

Revisar [05_remediation_proposal.md](05_remediation_proposal.md) y autorizar por separado las correcciones DB-02, DB-03 y la condición de evidencia DB-01, con aceptación en entorno aislado. No autorizar todavía eliminación general de guards/triggers o historial. Resolver las reglas D y la atribución interna pendiente de DB-01 antes de declarar cierre semántico completo.

Entregables: [inventario](01_postgresql_inventory.md), [clasificación](02_constraints_classification.md), [errores](03_known_errors_analysis.md), [dependencias](04_code_dependencies.md), [propuesta](05_remediation_proposal.md), este cierre y [bitácora](commands_and_evidence.md). Los anexos estructurales y de búsqueda están enlazados desde esos documentos. No contienen filas clínicas ni credenciales.

La auditoría se detiene aquí. No se aplicaron correcciones ni se inició Fase 2.
