# DBV2.2 — Evidencia PostgreSQL

Servidor: PostgreSQL 17.9 (Debian 17.9-1.pgdg13+1), server_version_num 170009.
Contenedor: capstone_v2_isolated_dbv22_contract_20260930.
ID: 9b235900a11fdf735c0d5c4502172139e35f0e2228f6f2c144e2b13b593061fd.
Imagen local: sha256:2a0d0fe14825b0939f78a8cad5cd4e6aa68bf94d0e5dd96e24b6d23af4315545.
Identificador de clúster: 7691343330713387048.
Base: postgres, creada automáticamente en este contenedor nuevo; usuario postgres sólo para esta reproducción mínima.
Host: socket Unix interno mediante docker exec; inet_server_addr NULL; sin puertos publicados.
Red: none. Almacenamiento: tmpfs /var/lib/postgresql/data; cero mounts de datos existentes.
Etiqueta: org.capstone.pgv2.purpose=DBV2.2-contract-probe.

Se verificaron identidad del contenedor, red, tmpfs, mounts, base y versión antes de ejecutar el SQL de escritura. No se utilizó .env ni conexiones del software. No se accedió a PostgreSQL operacional.

`contract_probe_container.json` conserva inspección; `contract_probe_identity.json` confirma versión y cero relaciones de aplicación/cero esquemas del reproducer después del ROLLBACK. `contract_trigger_probe.log` conserva salida real. No es una instalación ni certificación del catálogo BD-v2.

Para reproducir: crear un contenedor nuevo con postgres:17.9, --network none y --tmpfs /var/lib/postgresql/data; comprobar todos los atributos anteriores y server_version_num=170009 antes de ejecutar `psql -X -U postgres -d postgres` con `contract_trigger_probe.sql` por stdin. El SQL únicamente recrea las dos formas de fila y la expresión exacta del contrato, dentro de BEGIN/ROLLBACK. No ejecutar dbv2_1_target_schema.sql.

Contenedor temporal eliminado al finalizar; evidencia en contract_probe_cleanup.log.
