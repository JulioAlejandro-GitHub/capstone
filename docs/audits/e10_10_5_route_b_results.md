# E10.10.5D.4 — D-05/D-06 resueltas y adopción certificada

**E10.10.5D — ADOPCIÓN CERTIFICADA SOBRE COPIA AISLADA. PENDIENTE DE REVISIÓN Y APROBACIÓN.**

Gate D sigue pendiente de aprobación explícita. No habilita E ni cutover.

## 1. Objetivo alcanzado
D-05 conserva `assessment_identities.structural_hash text GENERATED ALWAYS AS (assessment_structural_hash(identity)) STORED`, nullable, con función y tres dependencias exactas a legacy. D-06 demuestra equivalencia individual de los cuatro CHECK; no se cambió ninguna restricción. Ruta A recertificada desde una instancia PostgreSQL 17.9 vacía nueva. Ruta B comprometió la adopción, cotejó catálogo completo, reconcilió datos y superó rollback intermedio, repetición y backup/restore.

## 2. Archivos modificados
Generador, recursos SQL, manifiesto, contrato `alembic_v2/d05_contract.json`, validación de recursos y catálogo, referencias fijadas del adaptador, `adoption_v2/check_catalog.py`, pruebas unitarias y runners aislados. Los seis entregables D, este informe, el informe estructural y los resultados de Ruta A se actualizaron. Inventario exacto en `e10_10_5d4_evidence/changed_files.txt`. Se conservaron baseline e informes anteriores en `previous_baseline/` y `previous_reports/`.

## 3. Comandos ejecutados
[Comandos y salidas](e10_10_5d4_evidence/command_results.json), [orquestación Ruta A](e10_10_5d4_evidence/route_a/orchestration.jsonl), [Alembic y fallo inyectado](e10_10_5d4_evidence/route_a/commands.jsonl), [operaciones Ruta B](e10_10_5d4_evidence/route_b/operation_commands.jsonl), [SQL del adaptador](e10_10_5d4_evidence/route_b/apply_statements.jsonl). Los runners finales retornaron 0. El subproceso de fallo A retornó 1 deliberadamente; B verificó SQLSTATE 22012 tras 50 DDL. No se registraron parámetros DML ni contraseñas.

## 4. Pruebas aprobadas, fallidas y omitidas
- 98 tests offline: 28 baseline y 70 adopción, incluidos los negativos D-04 y seis tests D-06. Validación estática, generador reproducible, lint y diff sin errores finales.
- Ruta A: instalación Alembic nueva; catálogo completo; 45 pruebas D-03, 5 D-05/D-06 de comportamiento y 46 científicas/E10. Generación, función resuelta y dependencias contrastadas además directamente contra legacy. Rollback después de 500 sentencias, idempotencia física y backup/restore de 103 tablas aprobados.
- D-06: 3.210 fixtures por catálogo (6.420 INSERT CHECK en total), predicados TRUE/FALSE/UNKNOWN, NULL, valores inválidos y límites. Las 27 combinaciones ternarias verifican también asociatividad AND/OR en la nueva Ruta A.
- Ruta B: preflight completo, 927 sentencias correctas (316 DDL), commit a `pg_v2_baseline`, reconciliación de 102 tablas de aplicación, cero diferencias injustificadas. Rollback auxiliar tras 50 DDL restaura exactamente 97 tablas, catálogo, head y secuencia. Repetición `already_adopted` sin cambios físicos. Backup/restore adoptado: 103 tablas, catálogo bruto, owners, ACL, head y secuencia exactos.
- Incidencias de desarrollo resueltas: un test mock de catálogo parcial provocó KeyError; se añadió rechazo explícito manteniendo la guarda. Un test nuevo buscaba `CREATE FUNCTION` en vez de `CREATE OR REPLACE FUNCTION`; se corrigió el test. Lint corrigió imports y estilo. Ningún cambio a datos científicos para superar pruebas.
- No quedan pruebas obligatorias D pendientes. No se ejecutaron E, cutover ni operaciones sobre origen. La preservación de tablas E10/campañas/evaluaciones vacías no prueba historial poblado; se informa como límite y se complementa con fixtures.

## 5. Evidencia reproducible
[Certificado nuevo](e10_10_5d4_evidence/route_a/certificate.json), [continuidad nativa](e10_10_5d4_evidence/route_a/contract_continuity.json), [matriz D-06](e10_10_5d4_evidence/d06_matrix.md), [preflight B](e10_10_5d4_evidence/route_b/preflight_result.json), [reconciliación](e10_10_5_data_equivalence.json), [catálogo](e10_10_5_catalog_diff.json), [rollback](e10_10_5d4_evidence/route_b/rollback_result.json), [repetición](e10_10_5d4_evidence/route_b/repeat_result.json), [restore](e10_10_5d4_evidence/route_b/restore_result.json).

Manifest vigente: `f276f819aa8512492ed89a52f12d192c1ace6cde24eee967287d17cd5f05dd57`. Catálogo Ruta A vigente: `6df01a4d0e8fbcfd3e65a23e1394902097e565adad6b1b99de56a90f342cfa68`. Catálogo bruto adoptado: `f7e4b81c604ab58a3285b4cdc49d7c3e3bbd46e74d5d118ad0b74444deb0b573`. Los hashes brutos difieren por los cuatro CHECK, no se normalizaron para hacerlos iguales. Los archivos de operaciones usan adicionalmente `adoption_v2.core.digest` (serialización tipada), identificado separadamente del SHA-256 JSON ordenado del certificado.

Plan: `57b3b5fb9d58d12339913b2f62f3921a3d34b1ea94cbe05f6901d9c0b4504112`. Correspondencias, origen, DDL y recibos comprometidos se conservan en archivo privado modo 0600/directorio 0700; su checksum está en `transformation_summary.json`. Backup adoptado: `e296e94bafad1c4e6a36430943bdd3ca9be3343d58a9d2172ed8338d1c5102df`. Los backups fuente originales permanecen exactos según `preserved_backups.json`. El inventario completo de evidencia y sus hashes está en `evidence_index.json`.

## 6. Diferencias frente al contrato
Cero diferencias injustificadas. Cuatro diferencias de representación CHECK explícitas y conservadas en el diff: TRIM/btrim sobre la misma función nativa; agrupaciones AND/OR asociativas manteniendo operandos, funciones, operadores, casts y dependencias. El comparador las limita a esas cuatro restricciones y exige bindings completos. Owners/ACL, pgcrypto, funciones, triggers, vistas, secuencias, integridad referencial y metadatos generados coinciden.
La revisión del manifiesto D-05 es aprobada por el usuario; D-03/B son evidencia histórica y no se usan para certificar esta baseline. No se ha alterado el contrato de pgcrypto D-04.

## 7. Riesgos pendientes
Revisión humana y aprobación Gate D. Certificación acotada al backup acreditado: usuario 1, modelos 3, source records 27.558, asignaciones 27.558, imágenes de splits 55.116; 83 tablas conservadas con hashes exactos. No se infiere evidencia histórica poblada para tablas vacías. Preservar backups privados y volúmenes antes de limpiar temporales. No se certifican aquí cutover, carga concurrente productiva ni etapa E.

## 8. Confirmación del estado operativo
Cero conexiones a PostgreSQL operativo durante D.4; ninguna modificación a archivos científicos, usuarios/credenciales operativos, datasets, splits, checkpoints, modelos, eventos/hashes originales ni migraciones históricas. Los 22 checksums y 54 archivos históricos siguen intactos. No se modificaron owners/ACL de pgcrypto ni pg_catalog. Únicamente hubo escritura en fixtures y copias aisladas acreditadas. Los tres contenedores aislados quedaron detenidos con volúmenes y backups conservados (`isolated_shutdown.json`). Sin E ni cutover.

## 9. Decisión solicitada
**Revisar la evidencia y aprobar explícitamente Gate D.** La aprobación no se presume ni autoriza iniciar E automáticamente.
