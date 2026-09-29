# E10.10.5D.2 — Decisión D-03 aplicada

D-03 fue aprobada expresamente por el usuario. D-01 y D-02 están **resueltos y comprobados** en PostgreSQL 17.9. **Gate D permanece bloqueado por D-04.**

## Corrección mínima aplicada
El generador aplica `alembic_v2/d03_contract.json` al AST del diseño conceptual, sin sustituir globalmente nombres. Conserva `experiment_execution_events.id bigint GENERATED ALWAYS AS IDENTITY NOT NULL`; retira CREATE SEQUENCE y ALTER SEQUENCE OWNED BY redundantes. PostgreSQL crea una sola secuencia con nombre/parametrización contractual y dependencia interna `i`. El manifiesto registra identity `a` (ALWAYS), nombre y parámetros; el entorno Alembic reconoce esa secuencia al repetir upgrade.
Solo los 39 pares tabla/columna del inventario aprobado reciben DEFAULT pg_catalog.gen_random_uuid(). Los defaults de entidades nuevas y las dos tablas MERGE quedan intactos; pgcrypto permanece. Un test compara todos los defaults anteriores/nuevos y exige que la diferencia sea exactamente ese conjunto de 39.
El comparador nativo ya incluía attidentity y pg_depend; ahora también coteja identity con el campo del manifiesto, todos los parámetros de su secuencia, las funciones resueltas de defaults y dependencias nativas. La captura legacy usa pg_catalog,public para obtener del servidor la misma representación del esquema histórico; no retira prefijos ni equipara funciones distintas. Para las 39 columnas exige igualdad de objetos/dependencias con Ruta A. La identidad/dependencia permanece nativa.

## Recertificación y continuidad
[Informe Ruta A nuevo](e10_10_5_route_a_results.md): instancia nueva, Alembic desde cero, comparación íntegra, 76 tests offline y 91 checks de servidor, rollback tras fallo SQL, idempotencia y backup/restore exacto de 103 tablas. La certificación B queda histórica, anterior a D-03. [Certificado y hashes](e10_10_5d2_evidence/route_a/certificate.json).
Solo después se restauró una nueva copia legacy y se repitió preflight. D-01 y D-02 pasan; 97 hashes/conteos, 22 checksums históricos, gate y estados correctos. [Resultado](e10_10_5d2_evidence/route_b/d03_resolution.json).

## D-04 — nuevo bloqueo, sin corrección automática
La guarda exige owner migrador en todas las funciones public y rechaza 36 funciones pgcrypto owner postgres. Las 36 entradas coinciden íntegramente con Ruta A; las 65 propias legacy sí son del migrador. Se detuvo antes del delta. No se modificó esta guarda, propietarios, ACL ni pg_catalog. [Diagnóstico exacto y propuesta](e10_10_5d2_evidence/route_b/owner_block_diagnosis.json).
Decisión solicitada: distinguir funciones propias (owner migrador obligatorio) de funciones de extensión (entrada completa exacta contra certificado, incluido owner/ACL), con tests negativos. Es autorización de D-04, no Gate D.

## Trazabilidad, código y comandos
[Informe de nueve puntos Ruta B](e10_10_5_route_b_results.md), [comandos offline](e10_10_5d2_evidence/static_commands.json), [comandos Ruta A](e10_10_5d2_evidence/route_a/orchestration.jsonl). Código: build_v2_baseline.py, validate_v2_static.py, v2_catalog_probe.py, verify_v2_route_a.py, alembic_v2/{env,resources}.py, adoption_v2/{core,execute}.py, tests/db_v2/test_static_baseline.py y runners D-03. Recursos y manifiesto regenerados; SQL históricos intactos.
[Diagnóstico D.1 anterior](e10_10_5d2_evidence/pre_d2_e10_10_5d_structural_resolution.md) y [baseline anterior](e10_10_5d2_evidence/previous_baseline/catalog_manifest.json) se conservan. D-03 no aplica reparación científica ni regeneración de valores. Cero conexiones operativas. No E ni cutover.
