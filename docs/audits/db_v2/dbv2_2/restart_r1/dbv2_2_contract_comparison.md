# DBV2.2 — Comparación del contrato

PASS — cero diferencias finales por identidad y definición.

1. Se archivó la candidata original en reference_candidate y se verificaron sus SHA-256 contra dbv2_1_source_evidence.json. Es referencia documental offline, no dependencia ejecutable del instalador.
2. baseline_delta.json enumera CURRENT_V2_BASELINE vs APPROVED_DBV21_R1_TARGET por tabla/columna, constraint, índice, función, trigger y vista. Los cambios son únicamente los ya aprobados por DBV2.1 y R1.
3. build_dbv22_baseline.py compara AST normalizados de cada identidad instalada con el SQL de diseño leído offline. Revalida todos los documentos derivados, columnas, FK, tipos, nulabilidad, defaults, claves, funciones, triggers, índices y views. El overlay E-04 se compara exactamente.
4. Las sentencias de recursos, verificadas contra DBV2.1 por AST, se normalizan en el servidor dentro de una base auxiliar y transacción revertida. No se instala el archivo de diseño ni se usa como bootstrap. expected_catalog.json registra ese EXPECTED; dbv2_2_catalog_manifest.json es ACTUAL leído de la instalación Alembic. El oracle de servidor no es científicamente independiente del contrato: la independencia procede de la comparación AST con DBV2.1 y las pruebas conductuales.
5. catalog_comparison.json compara 18 categorías completas, incluyendo columnas, defaults y dependencias, constraints/diferibilidad, índices/predicados, funciones/cuerpos/ACL, triggers, views, secuencias, tipos, extensiones, ownership, ACL de esquema/base/defaults, roles y privilegios efectivos. Cada categoría indica EXPECTED / ACTUAL / MATCH. Ninguna diferencia.

Los conteos solos no deciden aprobación. Se excluyen OID de base/objetos y nombres de la base del manifest canónico; se conservan attnum, definiciones, roles y ACL. La prueba de repetición verifica además OID/relfilenode en la misma base.

El índice PK de alembic_version es técnico: 413 de aplicación + 1 = 414. pgcrypto aporta funciones propias de extensión excluidas de las 79 funciones de aplicación. La tabla Alembic y el singleton técnico son las únicas filas persistidas.
