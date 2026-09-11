# E4 — Cierre operativo

El usuario aporta la ejecución Compose autorizada de `tests/test_campaigns_postgres.py::test_public_migration_readonly`, con `RUN_STAGE4_POSTGRES_TESTS=1`: **1 passed in 0.42s**. La prueba usa READ ONLY y comprueba revisión pública 20260911_02, cuatro tablas de campaña, índice de intento activo único y trigger de identidad TRAIN habilitado.

Se une a la evidencia previa de **49 casos sintéticos aprobados en 4,43 s**, incluida concurrencia y limpieza. Los **25 hashes** del manifiesto E4 final fueron comprobados al iniciar E5 sobre HEAD `cd5c64d703358797570f5183dd598d93314dc0eb`, árbol inicialmente limpio. Ambas ejecuciones son evidencia aportada por el usuario, no realizadas por este agente. No incluyen una captura independiente de hashes dentro del contenedor.

Dictamen actualizado: **E4 APROBADA en su alcance técnico**. Se conserva el historial de dictámenes pendientes. El resultado no acredita desempeño clínico, campañas extensas ni durabilidad ante reinicio. La selección de Producción Etapa 2 permanece manual.

La discrepancia de entrada registrada en `etapa_5_linea_base_2026-09-11.md` queda resuelta. E5 está autorizada por la solicitud del usuario; sus cambios y verificaciones deben identificarse separadamente. No se aplicaron migraciones por este registro.
