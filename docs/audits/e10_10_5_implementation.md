# E10.10.5D.4 — implementación vigente

**E10.10.5D — ADOPCIÓN CERTIFICADA SOBRE COPIA AISLADA. PENDIENTE DE REVISIÓN Y APROBACIÓN.**

D-05 añade un contrato explícito firmado por hash. El generador aplica la única corrección aprobada de columna, emite assessment_canonical y assessment_structural_hash en `02_generated_functions.sql` antes de tablas y elimina su emisión duplicada posterior. Las funciones conservan sus cuerpos. Manifiesto: attgenerated, expresión, tipo/nulabilidad y dependencias; carga verifica el hash del contrato. El verificador de Ruta A compara estos metadatos mediante catálogos nativos. La especificación conceptual histórica sigue congelada; las decisiones D-03/D-05 son overlays explícitos del compilador.

D-06 incorpora `adoption_v2/check_catalog.py`: captura conbin, pg_depend, funciones/operadores/tipos resueltos y propiedades completas de funciones. Referencia nativa de la nueva Ruta A fijada por SHA-256. Solo cuatro pares tabla/constraint admiten ubicaciones no semánticas, formato de btrim idéntico y asociación AND/OR ordenada; cada otra propiedad, binding y dependencia sigue exacta. Se guardan definiciones y hashes brutos distintos. No cambia DDL CHECK ni datos.

`execute.reconcile` conserva reconciliación científica y de secuencias y exige catálogo sin diferencias injustificadas antes de cambiar el head. Repetición y restore pasan por esa misma guarda. Restore exige adicionalmente igualdad bruta antes/después, sin aplicar normalización entre backup y restore. D-04 sigue intacta; suplemento de dependencias de funciones y pgcrypto verificado igual a la nueva A.

Runners D-05 crean nueva instancia y documentan recertificación. Runners de operaciones D-04 reutilizados con `PGV2_ADOPTION_EVIDENCE_DIR` apuntando exclusivamente a evidencia D.4, nuevas auxiliares `_d4_rollback`/`_d4_restore`, y sin sobrescribir informes antiguos. Diagnóstico D-06 y captura/reportes D-05 son reproducibles y guardados en `scripts/db/`. Toda restauración destructiva ocurre en auxiliares aisladas; no hay acceso al operativo.

Plan, snapshot fuente, delta SQL, correspondencias y recibos permanecen privados. Públicamente se registran inventarios, conteos, hashes, resultados y SQL sin parámetros. La recuperación está probada restaurando el dump adoptado en otra base y reconciliando las 103 tablas, estado técnico, owners y ACL. Las credenciales de entornos aislados permanecen fuera de informes.

[Certificado nuevo](e10_10_5d4_evidence/route_a/certificate.json) · [Matriz individual D-06](e10_10_5d4_evidence/d06_matrix.md) · [Cierre completo](e10_10_5_route_b_results.md). D-03/B y D.3 son históricos, conservados en sus directorios y `previous_reports/`.
