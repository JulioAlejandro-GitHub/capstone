# E10.10.5D.2 — Implementación D-03 y estado

**D-03 aplicada. Ruta A recertificada. D bloqueada por D-04.**

El generador modifica el AST mediante el contrato explícito `alembic_v2/d03_contract.json`: IDENTITY ALWAYS en la columna de eventos y calificación del núcleo en exactamente 39 defaults aprobados. Se elimina el recurso redundante de secuencia; se regeneran 03_tables, 10_privileges y manifiesto con identity y parámetros. `resources.py` verifica el hash de la decisión; `env.py` reconoce secuencias internas en la guarda de idempotencia.

El comparador incorpora funciones/dependencias de defaults y contrasta attidentity/parámetros contra metadatos del manifiesto. La captura de adopción usa representación nativa PostgreSQL bajo search_path explícito y exige el mismo binding/dependencias en las 39 columnas; no normaliza nombres de funciones distintas. Hash de manifiesto fijado por el adaptador: `6b499688b35ca748994df0f6914560b73bc36afbe3eb718d490376ac457ce1be`; catálogo recertificado: `a793026a0004a378375fe0b6c750ff0e6a6aeeb2c156e062282a1a025b895ac2`. Certificado en `e10_10_5d2_evidence/route_a/installed_catalog.json`, separado del certificado B histórico.

Runners nuevos: `recertify_v2_d03.py`, `test_v2_d03_server.py`, `preflight_v2_d03_adoption.py`. 76 tests offline y 91 comprobaciones PostgreSQL aprobadas; catálogo/rollback/idempotencia/restore de Ruta A certificados. Prueba de scope exacto impide cambiar defaults nuevos o MERGE por sustitución global.

Preflight D se detuvo antes de apply por `LEGACY_FUNCTION_OWNER_MISMATCH`: la guarda anterior aún exige migrador para funciones pgcrypto owner postgres. No se modificó esa guarda ni ownership/ACL. [Nueve puntos](e10_10_5_route_b_results.md), [resolución estructural](e10_10_5d_structural_resolution.md), [recertificación](e10_10_5_route_a_results.md). Código científico, historial, usuarios y backups fuente sin cambios. No E ni cutover. [Implementación previa](e10_10_5d2_evidence/pre_d2_e10_10_5_implementation.md).
