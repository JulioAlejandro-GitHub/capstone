# E5 — Diagnóstico de la comprobación pública

El usuario aporta **13 aprobadas y 1 fallida en 3,46 s**. La única prueba fallida es `test_public_e5_revision_readonly`, con AssertionError sanitizada. Ese resultado no permite saber si falla revisión, tablas o trigger; no demuestra por sí solo que la migración no se ejecutó.

Se modificó únicamente el diagnóstico de esa prueba: conserva las mismas exigencias (revisión 20260912_01, tres tablas y trigger habilitado), reúne las discrepancias en READ ONLY e informa fase/revisión observada/tablas faltantes/conteo de trigger. Se usa to_regclass para inspeccionar también el caso de tabla ausente sin provocar un error adicional. No se imprimen URLs, credenciales, parámetros operativos ni trazas del driver. Se elimina la etiqueta E4 incorrecta para esta comprobación E5.

Ruff aprobado; colección local correcta, 14 casos omitidos por ausencia del opt-in PostgreSQL. Esa omisión no se presenta como una validación funcional de la consulta. No se modificaron migraciones, implementación del ejecutor ni datos operativos. Los 13 resultados sintéticos aportados corresponden a su revisión previa; no acreditan este nuevo diagnóstico público.

Repetir sólo `tests/test_campaign_executor_postgres.py::test_public_e5_revision_readonly` con el mismo opt-in Compose. Si informa una revisión anterior o estructuras faltantes, revisar la salida de make db-migrate-check/make db-migrate antes de decidir la corrección. No aplicar migraciones saltando el wrapper ni interpretar la AssertionError como prueba de BD caída.

Dictamen: **E5 NO APROBADA**. Instalación pública pendiente de diagnóstico/verificación.
