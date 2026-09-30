# DBV2.2 — PostgreSQL real

PostgreSQL 17.9, versión numérica 170009. Imagen postgres:17.9 inspeccionada antes de provisionar.

- Contenedor: `capstone_v2_isolated_15ea056917ee` / `04b123ea4b4d453587dff975ac1ceadf0c43e6258707aee1e6e955942022c89e`.
- Host/puerto: 127.0.0.1:56439; no puertos operacionales 5432/5433.
- Base principal: `capstone_v2_isolated_15ea056917ee`; OID 16386.
- system_identifier: `7691348671323906093`.
- Volumen exclusivo: `capstone_v2_isolated_15ea056917ee`; etiqueta org.capstone.pgv2.isolation=15ea0569-17ee-47ab-b5ed-834dd26fe5d1.

Descriptor target.json; preflight_before_provision.json y latest_preflight.json acreditan identidad/roles. Las guardas verifican Docker local, volumen no compartido, ausencia de bind mounts/privilegios, URL/base exactas, versión, owner y sesión antes de DDL. Cada base auxiliar tiene descriptor propio verificado. commands.jsonl conserva comandos y salidas; nunca lee .env ni imprime credenciales de aplicación.

empty_catalog.json prueba ausencia de objetos de aplicación iniciales. Instalación exclusivamente Alembic; alembic_history.json contiene current/heads y raíz. empty_application_tables.json confirma cero filas científicas al finalizar, incluidos datasets, usuarios y nueve tablas XAI. Sólo el singleton técnico y el head tienen una fila.

Cero conexiones/escrituras a PostgreSQL operacional. Contenedor detenido, volumen conservado para revisión: disposable_environment_stopped.json. El entorno R1 mínimo era otro contenedor tmpfs sin red, eliminado: r1_cleanup.log.
