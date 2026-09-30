# SWV2.0 — Docker después

Captura completa (post restart Compose final): `swv2_0_docker_after.json`.

```
capstone-malaria
├── capstone_backend   (backend)   capstone-malaria-backend   0.0.0.0:8000
├── capstone_frontend  (frontend)  node:20                    0.0.0.0:80
└── capstone_db        (db)        postgres:17.9              127.0.0.1:5432  healthy
                                   volume capstone_v2_isolated_persistent_data → /var/lib/postgresql/data
```

| Recurso | Estado |
|---|---|
| Servicio PostgreSQL | `db` / contenedor `capstone_db` / proyecto `capstone-malaria` / red `capstone-malaria_default` / restart `always` |
| Volumen | `capstone_v2_isolated_persistent_data` (mismo CreatedAt 2026-09-30T16:28:37Z y labels `org.capstone.pgv2.*`); único usuario: `capstone_db` |
| Arranque | `Skipping initialization` + `database system was shut down at …` → mismo clúster, sin initdb |
| `capstone_db_v2` | contenedor eliminado (`docker rm`, sin `-v`), tras apagado limpio y verificación del nuevo servicio |
| Desechables `…fafc32d0d3a3`, `…1621252d7ab4` | contenedor + volumen propio eliminados tras reverificar: detenidos, sin proyecto Compose, volumen propio ≠ certificado |
| Legacy `capstone_db` | contenedor reemplazado por Compose; **volumen `capstone-malaria_postgres_data` conservado** (no referenciado por Compose; eliminación no autorizada en esta fase) |
| Otros `capstone_v2_isolated_*` detenidos (11) | sin tocar (fuera de alcance, ver JSON) |

## Cambios Compose versionados

- `docker-compose.yml`: `volumes.postgres_data` → `external: true`, `name: capstone_v2_isolated_persistent_data`. La clave lógica y el montaje del servicio (`postgres_data:/var/lib/postgresql/data`) no cambian. Compose no crea, inicializa ni elimina volúmenes externos (tampoco con `down -v`).
- `docker-compose.override.yml`: puerto `db` `"5432:5432"` → `"127.0.0.1:5432:5432"` (contrato DBeaver 127.0.0.1:5432; no expone el superusuario a la LAN).
- Sin cambios en `DATABASE_URL`, `.env`, backend ni frontend.

## Secuencia ejecutada

1. `docker compose stop backend frontend` → `docker compose stop db` (legacy).
2. `docker stop --timeout 60 capstone_db_v2` (checkpoint de shutdown limpio; puerto 5432 libre; 0 contenedores corriendo sobre el volumen).
3. `docker compose up -d --no-deps db` → recrea `capstone_db` sobre el volumen certificado → healthy → verificación `integrated` PASS.
4. `docker rm capstone_db_v2`; limpieza de los 2 desechables.
5. `docker compose up -d backend frontend` → contadores de escritura v2 sin cambios.
6. `docker compose down` (sin `-v`) + `docker compose up -d` → verificación `after_restart` PASS.
7. Creación autorizada del rol `julio` → verificación `post_role` + contrato DBeaver PASS.
8. Restart final `docker compose down` (sin `-v`) + `up -d` → `final_restart` + contrato DBeaver PASS.
