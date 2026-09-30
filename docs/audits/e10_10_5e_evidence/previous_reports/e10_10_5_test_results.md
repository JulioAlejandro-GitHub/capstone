# E10.10.5D.4 — resultados de pruebas

**E10.10.5D — ADOPCIÓN CERTIFICADA SOBRE COPIA AISLADA. PENDIENTE DE REVISIÓN Y APROBACIÓN.**

| Área | Resultado | Evidencia |
|---|---|---|
| Offline baseline | 28 PASS | e10_10_5d4_evidence/baseline_tests.out |
| Offline adopción | 70 PASS; negativos D-04 y D-06 incluidos | e10_10_5d4_evidence/adoption_tests.out |
| Estático/generador/lint | PASS; 22 checksums, 54 archivos históricos | static_results.json, generator_check.out, lint.out |
| Instalación A y catálogo | PASS, nueva instancia PG17.9 | route_a/installed_catalog.json |
| IDENTITY y UUID D-03 | 45 PASS | route_a/d03_server_tests.json |
| Generación y lógica ternaria | 5 PASS + contrato/dependencias nativas exactas | route_a/d05_server_tests.json, contract_continuity.json |
| Científicas/E10 | 46 PASS | route_a/server_tests.json |
| D-06 | 3.210 fixtures por catálogo, 6.420 CHECK reales | d06_native_and_tests.json, d06_matrix.md |
| A rollback/idempotencia/restore | PASS; 103 tablas restauradas | route_a/*_result.json |
| B preflight/adopción | PASS, commit pg_v2_baseline | route_b/preflight_result.json, apply_result.json |
| B datos/catálogo | PASS, 102 tablas app, 83 preservadas exactas, cuatro diferencias justificadas | e10_10_5_data_equivalence.json, e10_10_5_catalog_diff.json |
| B rollback intermedio | PASS tras 50 DDL; 97 tablas/head/catálogo/secuencia intactos | route_b/rollback_result.json |
| B repetición | PASS, already_adopted, filas físicas idénticas | route_b/repeat_result.json |
| B restore | PASS, 103 tablas, catálogo bruto, owners/ACL y secuencia exactos | route_b/restore_result.json |

Las rutas abreviadas se resuelven desde `e10_10_5d4_evidence/`. Los 27 triples booleanos se contabilizan dentro de un test servidor D-05/D-06; no son 27 tests adicionales. Pruebas de comportamiento de columna usan fixtures TEMP del contrato nativo, sin saltarse triggers en tablas científicas.

Fallos deliberados: subproceso A salida 1 / división por cero; B SQLSTATE 22012. Incidencias transitorias de tests/mock y lint corregidas se detallan en el cierre; cero fallos finales ni pruebas D obligatorias omitidas. E y cutover no ejecutados por alcance. Tablas históricas vacías no acreditan escenarios poblados; contratos cubiertos mediante fixtures. El parser estático es pglast PostgreSQL 18.4; la compatibilidad efectiva se verificó instalando y ejecutando en PostgreSQL 17.9 real, no se atribuye esa garantía al parser.
