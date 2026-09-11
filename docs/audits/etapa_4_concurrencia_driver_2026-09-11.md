# E4 — Proceso independiente y metadatos del driver

Evidencia del usuario: **48 aprobadas, 1 fallida, 1 deseleccionada en 4,46 s**. El único fallo es una AssertionError sanitizada en `test_concurrent_active_attempt_two_connections`. La salida no identifica su aserción ni acredita todavía el caso completo.

Se reprodujo localmente un defecto del proceso hijo: el bloqueo global de Path.read_text/read_bytes alcanza `psycopg.version → importlib.metadata → Path.read_text` al crear el engine, incluso sin abrir una conexión. Se obtiene AssertionError antes de consultar PostgreSQL. Esto prueba el defecto del test; aún debe confirmarse mediante repetición que explica el fallo comunicado.

Corrección limitada a pruebas: el guard bloquea lecturas bajo `configs` del proyecto, permitiendo metadatos de paquetes. Se mantiene la comprobación de que el registro de modelos no se importa, ahora también después de reconstruir la campaña. Se mantienen dos conexiones distintas, exactamente un intento creado y otro rechazado, lectura del intento activo, proceso independiente y limpieza del esquema sintético. Se añadieron mensajes controlados por fase para distinguir trabajadores, conexiones y proceso hijo sin imprimir stderr del driver.

Una regresión local ejecuta el mismo código de inicialización del hijo en otro intérprete, crea el engine sin conectar y verifica que leer configs sigue prohibido. Resultado del conjunto afectado: **61 aprobadas, 50 PostgreSQL omitidas**, dos avisos existentes Alembic. Ruff aprobado. No se modificó código funcional ni migraciones.

Repetir el comando Compose de toda la suite sintética proporcionado por el usuario. Esperado: **49 aprobadas y una deseleccionada**. E4 permanece **NO APROBADA**: integración completa e instalación pública pendientes. No se autoriza aplicar migraciones ni iniciar E5.
