# Resolución estructural vigente — E10.10.5D.4

**E10.10.5D — ADOPCIÓN CERTIFICADA SOBRE COPIA AISLADA. PENDIENTE DE REVISIÓN Y APROBACIÓN.**

D-05 aplicada: columna text nullable, GENERATED ALWAYS AS (assessment_structural_hash(identity)) STORED, attgenerated=s. Funciones emitidas antes de tablas en orden de dependencias; cuerpo y resolución preservados. No se recalcularon datos históricos. INSERT omitiendo el campo calcula hash; escritura explícita rechazada 428C9; UPDATE del identity regenera en fixture TEMP que copia la columna real. Tipo, expresión, función y tres dependencias son exactamente legacy; véase contract_continuity.json.

D-06: equivalencia individual demostrada de los cuatro CHECK. **[Matriz completa: expresiones legacy/Ruta A, dependencias, objetos resueltos, pruebas y decisión](e10_10_5d4_evidence/d06_matrix.md).** La conclusión combina árboles nativos y lógica ternaria con 6.420 comprobaciones CHECK efectivas. No se modificaron los CHECK; comparador limitado y tests negativos impiden ocultar cambios de operadores, casts, collation, función, dependencia o restricciones ajenas.

Ruta A nueva recertificada y Ruta B adoptada/reconciliada, con rollback, repetición y restore. Manifest y catálogo vigentes en `e10_10_5d4_evidence/route_a/certificate.json`; certificado D-03 conserva carácter histórico. Contrato D-04 de pgcrypto y dependencias intacto. [Nueve puntos, comandos, incidencias y resultados](e10_10_5_route_b_results.md).

---

# Historial previo (no describe el estado vigente)

# E10.10.5D.3 — D-04 resuelta; D-05/D-06 pendientes

**E10.10.5D — BLOQUEADA. GATE D NO APROBABLE.**

## D-04 implementada
La única guarda sustituida es la de ownership de funciones en capture(). `function_guard.py` comprueba inventario exacto, entradas nativas y pg_depend. Para las 65 propias: migrador, firma/definición/propiedades esperadas, ausencia de extensión y ACL NULL del restore autorizado --no-acl. No se ignora el ACL: cualquier otro valor bloquea. El delta ya existente instala después el ACL v2 y se compara íntegramente al final. Para las 36 pgcrypto: todos los campos, incluido owner postgres y proacl, idénticos a Ruta A D-03. No hay excepción general para postgres ni clasificación por nombre.
El suplemento de dependencias procede de lectura de Ruta A con su catálogo íntegro verificado contra el hash D-03. SHA-256 del suplemento: `af105f1a6a40b24a1beb7c758e77007d80db818417cc92277cd66fa87c4478bf`. Incluye dependencias nativas propias y de extensión; toda diferencia bloquea. Las referencias internas que PostgreSQL no registra para cuerpos PL/pgSQL no se inventan: las definiciones completas siguen comparándose.
14 tests nuevos cubren las nueve categorías negativas y casos adicionales. 90 tests offline aprobados. El preflight real pasó; no se modificaron propietarios ni ACL de pgcrypto.

## Ejecución y nuevo bloqueo
El adaptador recorrió el delta y reconcilió 102 tablas antes del cotejo final. FINAL_CATALOG_MISMATCH revirtió toda la transacción sin cambiar el head. Una auxiliar nueva reprodujo el catálogo discrepante con rollback obligatorio; ambas copias quedaron exactamente como antes.
D-05: columna `assessment_identities.structural_hash` generada almacenada en legacy, ordinaria sin expresión en Ruta A. No es representación. D-06: cuatro CHECK con diferencias de TRIM/btrim y asociación booleana; equivalencia pendiente, sin normalización aplicada. [Diff íntegro](e10_10_5d3_evidence/attempted_catalog_diff.json).
Se propone conservar generación legacy y ordenar assessment_canonical/assessment_structural_hash antes de la columna en baseline, tras aprobación y con nueva certificación. D-06 exige prueba nativa de identidad de operadores/funciones y semántica antes de tratarlo como formato. No se ha aplicado ninguna de estas correcciones.

## Evidencia y alcance
[Nueve puntos, comandos y decisión](e10_10_5_route_b_results.md). [Informe anterior D.2](e10_10_5d3_evidence/pre_d3_e10_10_5d_structural_resolution.md). Baseline y hashes D-03 permanecen inmutables durante D.3; su certificación de instalación no demuestra equivalencia con la columna generada legacy descubierta. No E, cutover ni acceso operativo. Gate D permanece no aprobable.
