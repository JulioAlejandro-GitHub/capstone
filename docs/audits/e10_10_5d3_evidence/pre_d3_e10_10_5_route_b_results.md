# E10.10.5D.2 — D-03 aplicada; nuevo bloqueo D-04

**E10.10.5D — BLOQUEADA. GATE D NO APROBABLE.**

## 1. Objetivo alcanzado
D-01 y D-02 corregidos conforme a D-03. Ruta A reconstruida en instancia PostgreSQL 17.9 nueva y recertificada antes de reintentar D. La copia legacy nueva supera las comprobaciones de identidad, datos, historia, IDENTITY y defaults, pero el preflight de captura se detiene en `LEGACY_FUNCTION_OWNER_MISMATCH`. No se ejecutó el adaptador.

## 2. Archivos modificados
Generador/contrato D-03, SQL y manifiesto, entorno Alembic, validadores, comparador, tests y documentación. `adoption_v2/core.py` fija los hashes nuevos; `execute.py` apunta al certificado nuevo y usa representación nativa PostgreSQL para el esquema legacy, cotejando además los objetos/dependencias de los defaults y attidentity. **La guarda de ownership que bloquea no fue modificada.** Runners nuevos: recertificación, tests D-03 y preflight de copia. [Detalle estructural](e10_10_5d_structural_resolution.md).

## 3. Comandos ejecutados
Comandos de Ruta A y salidas 0 en su [informe](e10_10_5_route_a_results.md). Después:
```
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python scripts/db/preflight_v2_d03_adoption.py
```
Salida **2**, bloqueo esperado por guarda real `LEGACY_FUNCTION_OWNER_MISMATCH`. Restore previo salida 0, backup aislado salida 0. SELECT/lecturas para diagnóstico; no apply, DDL de adopción, stamp ni transición de head. [Restore exacto](e10_10_5d2_evidence/route_b/restore.json), [preflight](e10_10_5d2_evidence/route_b/preflight_result.json).

## 4. Pruebas aprobadas, fallidas y omitidas
Aprobadas: recertificación completa Ruta A; 97 conteos/hashes de copia coinciden con referencia D; 22 checksums históricos; revisión 20260922_01; gate libre, estados inactivos, tres modelos y un usuario. Sin otras sesiones en la base destino. D-01 secuencia/dependencia/attidentity idénticos a Ruta A; D-02 esquema renderizado legacy exacto y bindings/dependencias de 39 defaults iguales al certificado.
**Fallida:** guarda LEGACY_FUNCTION_OWNER_MISMATCH.
**Omitidas por bloqueo:** apply/adopción completa, catálogo adoptado, equivalencia adoptada, rollback intermedio de adopción, repetición y backup/restore adoptado. Las pruebas de Ruta A no sustituyen estas pruebas.

## 5. Evidencia reproducible
Base nueva `capstone_v2_isolated_8c5114865703_d2_adoption`, OID 26241, clúster aislado `7691066755790737451`, puerto 55479; descriptor/identidad verificados antes de restaurar. No se reutilizó ni modificó la copia D original. Se restauró el backup fuente conservado, SHA-256 `fa50d1dedb10e2a04aa99125143f2b74c213eceb679db1e69ffc1d9a882b71f6`, y se obtuvo backup privado de esta nueva copia.
[Inventario y hashes](e10_10_5d2_evidence/route_b/reference_inventory.json), [preservación](e10_10_5d2_evidence/route_b/preservation.json), [D-01/D-02 resueltos](e10_10_5d2_evidence/route_b/d03_resolution.json), [diagnóstico D-04](e10_10_5d2_evidence/route_b/owner_block_diagnosis.json). No se publican credenciales ni filas científicas.

## 6. Diferencias frente al contrato
**D-04:** `capture()` exige owner `capstone_v2_migrator` para todas las funciones public. Las **36** funciones de pgcrypto son owner `postgres`, igual que en Ruta A nueva (y en la anterior). Sus entradas nativas completas coinciden exactamente con el certificado: definición, firma, pertenencia a extensión, owner, ACL y propiedades. Las **65 funciones propias legacy** sí pertenecen al migrador. No es pérdida científica ni justifica ALTER OWNER sobre pgcrypto; es una guarda que no distingue funciones propias de funciones administradas por la extensión.
La corrección de D-03 no incluyó modificar esta guarda. Se cumple la instrucción de detenerse ante un bloqueo nuevo. No se normalizó ownership, no se concedieron privilegios ni se modificó pg_catalog.

## 7. Riesgos pendientes
D-04 impide continuar; pueden aparecer otras guardas al reanudar. Los datos legacy de campañas/runs/eventos están vacíos: aun con adopción futura no habrá prueba de preservación de historial poblado. Los backups fuente permanecen privados en /private/tmp y deben conservarse. La equivalencia actual corresponde a restauraciones del backup conservado, no a una nueva captura del operativo. [Riesgos](e10_10_5_open_risks.md).

## 8. Confirmación del estado operativo
**Cero conexiones al PostgreSQL operativo en D.2.** No se cambiaron datos científicos, usuarios/credenciales de aplicación, asignaciones, modelos/checkpoints, eventos/hashes, ledger ni backups fuente. Las únicas escrituras de datos legacy fueron el restore autorizado en una base auxiliar nueva. Las pruebas destructivas/sintéticas ocurrieron exclusivamente en Ruta A aislada. Los dos contenedores aislados se detuvieron conservando volúmenes. No E ni cutover.

## 9. Decisión solicitada
**Autorizar D-04: exigir owner migrador para funciones propias y cotejar las funciones de extensión contra sus entradas completas en Ruta A certificada, manteniendo owner postgres y ACL originales.** No ALTER OWNER, GRANT ni cambios a pgcrypto. Añadir tests que rechacen cambios de propietario, ACL, definición o pertenencia a extensión; después repetir preflight y, si pasa, continuar D.
No se solicita Gate D porque la adopción y sus pruebas aún no están certificadas.
