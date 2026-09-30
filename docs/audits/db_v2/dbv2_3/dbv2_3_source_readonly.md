# Protección del origen

Fuente acreditada: contenedor `capstone_db` / `2604ff9884655b3b78ffc85997cbe30d6392afca7b904b5df2b37dacedb30d89`; proyecto compose capstone-malaria, servicio db; base `malaria_experiments`; host lógico capstone_db; puerto publicado 5432; volumen `capstone-malaria_postgres_data`; system_identifier `7668020338728398886`.

Se contrastaron las identidades POSTGRES_DB/POSTGRES_USER de configuración existente sin registrar contraseñas. Cada conexión psql usa PGOPTIONS=-c default_transaction_read_only=on, BEGIN READ ONLY y ROLLBACK. Se verifica current_database, current_user, versión, identidad de cluster y ambos parámetros read_only=on. Sólo se emitieron SELECT de catálogo/conteos/coherencia; cero DDL/DML de escritura.

source_identity.json y source_readonly_queries.jsonl contienen identidad y sentencias. source_catalog.json contiene exclusivamente metadata estructural. No se consultó el valor de password_hash; sólo aparece como nombre/tipo de columna. No se registraron passwords ni hashes de contraseñas.

SOURCE != DESTINATION acreditado antes del primer SQL de escritura: distintos contenedores, puertos (5432 vs 56440), bases, volúmenes y system_identifier. Comparten host físico, pero nunca conexión, cluster o almacenamiento. source_destination_separation.json y before_first_destination_sql_write.json conservan la prueba. Las guardas la revalidan antes de operaciones de destino.

Escrituras al origen emitidas por esta fase: **0**. No cambios de conexiones de aplicación, permisos, triggers, tablas, datos ni migraciones del origen.
