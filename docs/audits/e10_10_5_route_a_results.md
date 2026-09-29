# Ruta A — recertificación D.4

**APROBADA TÉCNICAMENTE SOBRE INSTANCIA NUEVA AISLADA; revisión humana pendiente.**

Se recertifica D-05 después del diagnóstico D-06. La certificación B y D-03 es histórica: manifest `6b499688b35ca748994df0f6914560b73bc36afbe3eb718d490376ac457ce1be`, catálogo `a793026a0004a378375fe0b6c750ff0e6a6aeeb2c156e062282a1a025b895ac2`. Los resultados antiguos están conservados en `e10_10_5d4_evidence/previous_reports/` y en sus directorios originales; no acreditan la baseline actual.

Nuevo manifest `f276f819aa8512492ed89a52f12d192c1ace6cde24eee967287d17cd5f05dd57`; nuevo catálogo `6df01a4d0e8fbcfd3e65a23e1394902097e565adad6b1b99de56a90f342cfa68`. Instancia nueva `capstone_v2_isolated_e662bcacb2fb`, puerto 55481, system identifier 7691087240586227755, volumen y credenciales independientes, PostgreSQL 170009. Descriptor mantiene el formato de seguridad B y añade `recertification_stage=E10.10.5D.4`; no es una reutilización de su certificado.

Instalación vacía Alembic, catálogo íntegro, 45 pruebas D-03, 5 pruebas D-05/D-06, 46 científicas/E10, generación/dependencias exactas a legacy, rollback real tras 500 sentencias, idempotencia y restore de 103 tablas aprobados. Datos y secuencia tras restore coinciden exactamente (en A, secuencia sintética 2,true; en B legacy se mantiene 1,false). El cotejo estructural instala independientemente el manifiesto en otra base de referencia; no se presenta ese render como oráculo científico independiente: se complementa con contratos, pruebas negativas y comparación legacy.

La columna generada se prueba en tabla TEMP creada `LIKE ... INCLUDING GENERATED`, que copia el contrato físico real y permite aislar su regeneración de triggers de inmutabilidad de negocio. Ninguna fila histórica se recalculó. Función, tipo, nulabilidad y tres dependencias se comparan además con el catálogo legacy. D-06 del diagnóstico inicial coincide exactamente con el contrato de la nueva A.

[Certificado](e10_10_5d4_evidence/route_a/certificate.json) · [Comandos](e10_10_5d4_evidence/route_a/orchestration.jsonl) · [Continuidad](e10_10_5d4_evidence/route_a/contract_continuity.json) · [Restore](e10_10_5d4_evidence/route_a/restore_result.json) · [Cierre de nueve puntos](e10_10_5_route_b_results.md).

Backup A SHA-256 `8678bd18ff671363242e424c8de4d088acb0b626aec17f6922c11e9c4eaaa2a2`; archivo trasladado a directorio privado después del restore, sin cambiar bytes, registrado en `route_a/backup_location.json`. Contenedor detenido, volumen conservado. No acceso operativo ni E/cutover.
