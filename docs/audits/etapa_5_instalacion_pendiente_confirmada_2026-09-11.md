# E5 — Instalación pública pendiente confirmada

La prueba READ ONLY ejecutada por el usuario devuelve: revisión esperada 20260912_01, obtenida 20260911_02; faltan campaign_execution_events, train_execution_records y train_execution_sessions; cero triggers train_record_guard habilitados. Resultado: una prueba fallida en 0,37 s.

Esta evidencia confirma que la migración E5 no está instalada en la base consultada. No contradice los trece casos sintéticos aprobados: aquellos aplican las migraciones dentro de esquemas temporales y los limpian al terminar.

Se revisó scripts/db/migrate.sh: current/heads, verificación de adopción, backup, preflight transaccional, upgrade head y current/heads finales. El nuevo intento de make db-migrate-check desde esta sesión volvió a fallar por acceso denegado a Docker API; no llegó a PostgreSQL. No se aplicaron migraciones ni se modificó código.

Siguiente paso autorizado por la solicitud E5: ejecutar make db-migrate-check en la terminal del usuario y, únicamente si pasa, make db-migrate. Conservar y revisar cualquier fallo del wrapper; no saltar backup ni preflight. Tras el éxito, ejecutar la suite E5 completa y las comprobaciones posteriores del procedimiento.

Dictamen E5: NO APROBADA hasta acreditar instalación y comprobaciones operativas. No se inició E6 ni una campaña científica.
