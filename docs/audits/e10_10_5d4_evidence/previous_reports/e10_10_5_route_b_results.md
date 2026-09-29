# E10.10.5D.3 — D-04 resuelta; catálogo final bloqueado

**E10.10.5D — BLOQUEADA. GATE D NO APROBABLE.**

## 1. Objetivo alcanzado
D-04 aplicada exclusivamente a la guarda de funciones. El preflight completo pasó y se ejecutó el adaptador sobre la copia PostgreSQL 17.9 aislada acreditada. Todas las sentencias SQL terminaron correctamente y las 102 tablas de aplicación se reconciliaron antes del cotejo final. La comparación íntegra de catálogo bloqueó el commit con FINAL_CATALOG_MISMATCH. No se cambió el head. El rollback dejó íntegros catálogo, 97 tablas legacy y secuencia.
No se declara adopción certificada ni se ejecutan pruebas posteriores que presuponen un destino adoptado.

## 2. Archivos modificados
`adoption_v2/function_guard.py` nuevo y sustitución de la única guarda de ownership en `adoption_v2/execute.py`. `tests/adoption_v2/test_function_guard.py` añade 14 tests. Runners aislados de captura de dependencias, ejecución trazada, diagnóstico con rollback y preparación de operaciones futuras. Informes y evidencia actualizados.
**Sin cambios a baseline, manifiesto, propietarios reales, ACL de pgcrypto ni certificados D-03.** Se conservaron los cambios D.2 preexistentes; no se presentan como modificaciones nuevas de D.3. Los runners de repetición/restore/inyección están preparados pero no ejecutados.

La guarda exige inventario exacto de 65 funciones propias legacy + 36 funciones pgcrypto. Para propias: owner migrador, firma/definición/propiedades exactas y ausencia de extensión; ACL exactamente NULL, correspondiente al restore autorizado `--no-acl`. Este es el contrato **previo** a adopción, no una equivalencia silenciosa con el ACL v2. El delta existente instala luego los ACL v2 y la comparación final los exige. Para pgcrypto: entrada completa idéntica a Ruta A, sin excepción para owner postgres. `pg_depend`/`pg_extension` acreditan pertenencia; un suplemento de dependencias leído de Ruta A se fija por checksum. Las dependencias de todas las funciones deben coincidir con el subconjunto contractual.

## 3. Comandos ejecutados
Entornos: solo contenedores aislados D y Ruta A D-03. Nunca PostgreSQL operativo.

```
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python /private/tmp/d04_dependency_reference.py
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python -m unittest discover -s tests/adoption_v2 -v
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python -m unittest discover -s tests/db_v2 -v
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python scripts/db/certify_v2_d04_adoption.py preflight
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python scripts/db/certify_v2_d04_adoption.py apply
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python scripts/db/certify_v2_d04_adoption.py diagnose
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python scripts/db/diagnose_v2_d04_catalog.py
```
Todos salida 0 salvo `apply`, salida **2** (`FINAL_CATALOG_MISMATCH`). El script temporal de dependencias se conserva como `scripts/db/capture_v2_d04_dependencies.py` (formato/imports ordenados). Comandos Docker de auxiliares en operation_commands.jsonl. Los nombres/directorios privados se usan una sola vez; los runners rechazan reutilizar archivos o bases existentes. No reejecutar estos nombres conservados a ciegas.

## 4. Pruebas aprobadas, fallidas y pendientes
- **90 tests offline aprobados:** 64 adopción (50 anteriores + 14 D-04), 26 baseline/Alembic.
- Nueve categorías negativas requeridas cubiertas: owner propio, owner extensión, ACL, definición, firma, pertenencia, función inesperada, función ausente y reclasificación. Además: dependencias alteradas/ausentes, firma duplicada y propiedad de seguridad cambiada. Son fixtures nativas en memoria; no se alteró pgcrypto en PostgreSQL para probar rechazos.
- Preflight real completo aprobado, incluidas 97 tablas, revisión legacy, 22 checksums, gate libre/estados, tres modelos, usuario, referencias/hash de datos y D-01/D-02/D-04.
- Ejecución real: **838 sentencias registradas correctas**, incluidas **316 DDL**; cero errores SQL. Falló exclusivamente la guarda final del catálogo. Reconciliación precommit de 102 tablas y secuencia alcanzada; no certificado duradero.
- Rollback real del fallo final: PASS, catálogo y 97 tablas exactos; head `20260922_01`, secuencia `1,false`.
- Diagnóstico en una base auxiliar nueva: mismo delta; catálogo final capturado y rollback obligatorio antes del commit. Comparación completa antes/después exacta.
- **Pendientes/no ejecutados:** adopción comprometida, inyección del fallo intermedio en la sentencia 50, repetición segura sobre adoptado, backup/restore adoptado y verificación posterior. El rollback real observado no se presenta como el ensayo de inyección intermedia aún pendiente.

## 5. Evidencia reproducible
[Preflight](e10_10_5d3_evidence/preflight_result.json), [inventario](e10_10_5d3_evidence/preflight_inventory.json), [suplemento de dependencias](e10_10_5d3_evidence/route_a_function_dependencies.json), [tests](e10_10_5d3_evidence/adoption_tests.out), [sentencias de adopción](e10_10_5d3_evidence/apply_statements.jsonl), [resumen](e10_10_5d3_evidence/execution_summary.json), [diff exacto](e10_10_5d3_evidence/attempted_catalog_diff.json), [rollback](e10_10_5d3_evidence/after_failure.json), [rollback auxiliar](e10_10_5d3_evidence/diagnostic_rollback.json).
Plan, snapshots y archivos reversibles se conservan privados fuera del repositorio, modo 0600/directorios 0700; sin credenciales ni filas privadas en informes. Plan preflight SHA-256 `6f75e4be3ab64bfd991ae06ef39c717f688c2acebb8d08b4ada2ccd6fee7e1e1`. Los parámetros DML no se registran en los logs públicos. El plan de cada ejecución conserva su propio origen/base en archivo privado; no se sustituyen entre copias.
Certificado utilizado exclusivamente D-03: manifiesto `6b499688b35ca748994df0f6914560b73bc36afbe3eb718d490376ac457ce1be`, catálogo `a793026a0004a378375fe0b6c750ff0e6a6aeeb2c156e062282a1a025b895ac2`. Ambos intactos.

## 6. Diferencias frente al contrato
**D-05 — incompatibilidad arquitectónica real:** `assessment_identities.structural_hash` es en legacy una columna GENERATED ALWAYS AS (assessment_structural_hash(identity)) STORED (`attgenerated=s`), y permanece así durante adopción. Ruta A certificada espera `text` ordinario, sin expresión ni generación. Son distintos contratos de escritura/cálculo, aunque esta tabla esté vacía. La comparación también muestra la función y tres dependencias del atributo generado, ausentes en Ruta A. No se eliminó la generación ni se inventaron hashes para hacer pasar el cotejo.

**D-06 — cuatro CHECK con representación divergente**, sin equivalencia certificada:
1. campaign_controlled_requests.campaign_controlled_requests_reason_check: TRIM(BOTH FROM reason) frente a btrim(reason).
2. cell_predictions.ck_cell_prediction_label_index: agrupación OR.
3. smear_analysis_summaries.ck_smear_summary_fraction: agrupación AND.
4. smear_analysis_summaries.ck_smear_summary_probabilities: agrupación AND.
No se descartan como formato ni se normalizan. Requieren comprobar operadores/funciones realmente resueltos y semántica de tres valores, no solo similitud textual. Las demás categorías del catálogo coinciden; owners/ACL, funciones completas, extensiones y secuencias no presentan diferencias finales.

## 7. Riesgos pendientes
D-05 impide certificar; D-06 permanece sin resolver. La futura corrección de baseline requiere conservar la generación y ordenar sus dependencias: assessment_canonical, luego assessment_structural_hash, antes de crear la columna, o una instalación equivalente acreditada; no cambiar la secuencia científica ni datos para adaptarse a un objetivo incorrecto. Se necesita una nueva recertificación si cambia el manifiesto; el certificado D-03 seguiría histórico.
No se ha probado repetición/restore adoptado porque no existe destino adoptado. El dataset real permanece protegido por los hashes y rollback; los eventos/runs/campañas legacy están vacíos, por lo que no se afirma cobertura de historial poblado. Archivos privados y backups deben conservarse para reanudar.

## 8. Confirmación del estado operativo
**Cero conexiones al PostgreSQL operativo durante D.3.** No se modificaron archivos científicos, usuarios/credenciales operativos, asignaciones, modelos/checkpoints, eventos/hashes originales, historial ni backups fuente. Ningún ALTER OWNER ni GRANT/REVOKE sobre pgcrypto. Las escrituras del adaptador ocurrieron exclusivamente en copias aisladas y se revirtieron. Los dos contenedores aislados quedaron detenidos, con volúmenes/backups/evidencia conservados. Sin E ni cutover.

## 9. Decisión solicitada
**Autorizar D-05 para conservar la columna generada legacy en la baseline, con orden de dependencias correcto y nueva recertificación de Ruta A; autorizar el diagnóstico de D-06 y su tratamiento como representación solo si se demuestra equivalencia nativa de funciones/operadores/dependencias y comportamiento.** No se solicita permiso para eliminar la generación ni para omitir constraints.
Gate D no se solicita: adopción, catálogo final y pruebas restantes no están certificados. La pausa cumple la instrucción expresa de detenerse ante una nueva incompatibilidad arquitectónica.
