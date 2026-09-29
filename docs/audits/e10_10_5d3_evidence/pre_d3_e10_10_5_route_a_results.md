# E10.10.5D.2 — Ruta A recertificada tras D-03

**RUTA A RECERTIFICADA EN POSTGRESQL 17.9. D SIGUE BLOQUEADA POR D-04.**

## 1. Objetivo alcanzado
D-03 aplicada: `experiment_execution_events.id` conserva GENERATED ALWAYS AS IDENTITY; PostgreSQL crea una sola secuencia con dependencia interna. Solo los 39 defaults UUID retenidos aprobados pasan a `pg_catalog.gen_random_uuid()`. pgcrypto se conserva. Las entidades nuevas y las dos tablas MERGE no reciben cambios de defaults. Una instancia nueva y vacía se instaló mediante Alembic y superó todas las pruebas de Ruta A.

## 2. Archivos modificados
Generador, contrato `alembic_v2/d03_contract.json`, recursos 03/10 y manifiesto; eliminado 02_sequences.sql redundante. `env.py` incluye secuencias IDENTITY en la guarda de segunda ejecución; `resources.py` verifica el hash de D-03. Validador estático, comparador nativo, tests estáticos/servidor y documentación actualizados. No se modificó la especificación conceptual histórica ni los 54 archivos históricos.

## 3. Comandos ejecutados
[Ocho comandos estáticos](e10_10_5d2_evidence/static_commands.json), [orquestación nueva](e10_10_5d2_evidence/route_a/orchestration.jsonl), [subcomandos de instalación y pruebas](e10_10_5d2_evidence/route_a/commands.jsonl).

Comando base: `PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python scripts/db/recertify_v2_d03.py ACCION`, con `setup`, `preflight`, `upgrade`, `catalog`, `d03`, `server`, `rollback`, `idempotence`, `backup_restore`. Todos salida 0. `catalog` se repitió al añadir cotejos directos de metadatos IDENTITY y parámetros/dependencia de secuencia; todos los cotejos resultaron exactos.
El runner usa un descriptor nuevo y rechaza sobrescribir setup. Los nombres/puertos/directorio del runner corresponden a este ensayo conservado; para otra reproducción deben seleccionarse recursos y evidencia nuevos, nunca reutilizar a ciegas los existentes. Credenciales y pgpass permanecen fuera del repositorio.

## 4. Pruebas
- 76 tests offline: 26 baseline/Alembic + 50 adopción sintética. Ocho comandos offline aprobados; Ruff y formato correctos.
- Instalación Alembic desde cero, head `pg_v2_baseline`.
- Catálogo completo y metadatos: cero diferencias. Incluye attidentity, pg_depend interno, parámetros de secuencia, funciones resueltas de defaults y dependencias, además de todas las categorías anteriores, owners y ACL.
- 46 comprobaciones existentes de servidor + 45 D-03 = **91 aprobadas**. D-03 prueba estado inicial `1,false`, INSERT sin ID, rechazo 428C9 de ID explícito, OVERRIDING SYSTEM VALUE, inmutabilidad de evento global, 39 bindings del núcleo y ejecución sin permiso sobre el wrapper de pgcrypto.
- Fallo SQL real tras 500 CREATE/ALTER: rollback completo; sin tablas/funciones propias/head parcial.
- Segunda ejecución Alembic: catálogo, filas/xmin/ctid y secuencia sin cambios.
- Backup/restore 17.9: 103 tablas con datos sintéticos, catálogo y secuencia iguales. Estado restaurado de secuencia `2,true`, producido explícitamente por los probes sintéticos; no se confundió con estado inicial.
No quedan pruebas de Ruta A fallidas u omitidas. No son pruebas de adopción de datos legacy.

## 5. Evidencia y hashes
Instancia `31a156221505e7bca249072281dd793833dbb91a5bd03de50114748463c2a194`, volumen/base `capstone_v2_isolated_e09f641a23c5`, puerto 127.0.0.1:55480, cluster `7691073295770107948`, OID 16386. Roles separados con credenciales aleatorias nuevas. [Preflight](e10_10_5d2_evidence/route_a/preflight_before_alembic.json).

Manifiesto nuevo: `6b499688b35ca748994df0f6914560b73bc36afbe3eb718d490376ac457ce1be`.
Catálogo nuevo: `a793026a0004a378375fe0b6c750ff0e6a6aeeb2c156e062282a1a025b895ac2`.
Backup Ruta A: `219b651a4ed9d9ec6c27f5bc26d998ad33893b7bd00dbb39ed8b42e3cb72465c`.
Datos fuente/restaurados: `edda1543b349d9c34bfdc12c0c4af12718d774075d09422b59184794d9cc078d`.
[Certificado](e10_10_5d2_evidence/route_a/certificate.json), [diff](e10_10_5d2_evidence/route_a/catalog_result.json), [restore](e10_10_5d2_evidence/route_a/restore_result.json).

## 6. Diferencias frente al contrato anterior
D-03 corrige dos pérdidas semánticas demostradas en D.1; no normaliza objetos distintos como equivalentes. El generador usa un overlay explícito de 39 pares tabla/columna, probado contra el inventario autorizado. El manifiesto incluye identity y sus parámetros; el comparador contrasta tanto la representación de PostgreSQL como esos metadatos. Nuevas categorías de catálogo (`default_functions`, `default_dependencies`) forman parte del hash nuevo.
La certificación B anterior corresponde a manifiesto `c1063136941e9429373d91d666fbea5d25afd0dc39f111fdf2b9779aa1f51eb0` y catálogo `df07e6bfc58c21f8290ffb63324a8f3e57b4561e4fe12be74ce576be993fc58b`. Se conserva en `e10_10_5b_evidence/run_b01/` y [reporte previo](e10_10_5d2_evidence/pre_d2_e10_10_5_route_a_results.md). **No se reutilizaron resultados B para certificar la baseline nueva.**

## 7. Riesgos pendientes
Ruta B encontró D-04: guarda de ownership incompatible con las 36 funciones de pgcrypto que pertenecen a postgres tanto en copia como en este certificado. D sigue bloqueada; [informe Ruta B](e10_10_5_route_b_results.md). No se acredita recorrido de aplicación E.

## 8. Estado operativo
Cero conexiones al origen en D.2. Sin modificaciones de usuarios/datos científicos/checkpoints/eventos originales, historial ni backups fuente. Instancias aisladas detenidas al cierre; volúmenes y backups conservados.

## 9. Decisión solicitada
No se solicita Gate D. Se requiere decisión D-04 sobre la guarda de funciones de extensión antes de reanudar adopción. No E ni cutover.
