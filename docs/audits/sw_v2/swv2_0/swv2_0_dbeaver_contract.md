# SWV2.0 — Contrato DBeaver

| Campo | Contrato | Estado |
|---|---|---|
| Host | 127.0.0.1 | PASS — `capstone_db` publica `127.0.0.1:5432` |
| Port | 5432 | PASS |
| Database | malaria_experiments | PASS — BD-v2, OID 16386, sysid 7691366089693499436 |
| PostgreSQL role | julio | PASS — autenticación SCRAM correcta |
| JDBC | `jdbc:postgresql://127.0.0.1:5432/malaria_experiments` | contrato probado con driver psycopg (equivalente) |

## Resolución del rol (autorización explícita del usuario "AUTORIZACIÓN SWV2.0 — RESOLVER POSTGRES LOGIN julio")

1. Intento inicial (`swv2_0_dbeaver_attempt.json`): el rol no existía; la creación de un superusuario quedó pendiente de autorización.
2. Precheck vía PostgreSQL (`swv2_0_role_precheck.json`, sesión READ ONLY): sysid 7691366089693499436, `malaria_experiments` OID 16386, `julio` ausente en `pg_roles` y `pg_authid`.
3. `CREATE ROLE julio WITH LOGIN SUPERUSER PASSWORD <verificador SCRAM>` (`swv2_0_role_julio.json`). La contraseña es la ya configurada para el entorno (`POSTGRES_PASSWORD` de `.env`, la usada por DBeaver/backend); se leyó en memoria, libpq calculó el verificador SCRAM-SHA-256 en el cliente, el texto plano nunca se envió ni se registró; sesión con `log_statement=none` y `log_min_error_statement=panic`. Sin GRANT, sin cambios de ACL/ownership, sin roles adicionales.

Finalidad del SUPERUSER: conservar el contrato administrativo local existente (el `julio` legacy era superusuario) sin modificar `database_acl`, que forma parte del manifest estructural. El rol es de clúster y **no** es una modificación de `pg_v2_baseline`.

## Prueba equivalente a DBeaver (como `julio`)

Ejecutada tras crear el rol (`swv2_0_dbeaver_contract_post_role.json`) y tras el restart Compose final (`swv2_0_dbeaver_contract_final_restart.json`), con idéntico resultado:

| Verificación | Resultado |
|---|---|
| Autenticación `julio` | PASS |
| current_database() | malaria_experiments |
| server_version | 17.9 (Debian 17.9-1.pgdg13+1) |
| sysid / OID | 7691366089693499436 / 16386 |
| Tablas de aplicación / views | 104 / 33 |
| XAI | xai_method_configurations, xai_evidence, xai_artifacts, xai_region_attributions, xai_evaluation_protocols, xai_quantitative_evaluations, xai_evaluation_members, xai_interpretations, xai_specialist_reviews (9) |
| xai_explanations | ausente |
| alembic_version | pg_v2_baseline |
| Dataset | FROZEN, 22,180 / 2,693 / 2,685 = 27,558, 201 pacientes, overlap 0/0/0, snapshot = DBV2.5 |

## DBeaver (cliente)

No se automatizó ni modificó DBeaver. Pendiente del usuario: **Test Connection** en la conexión existente. Si PostgreSQL pasa y DBeaver falla, es configuración/credencial del cliente; la BD no se modifica.

## Separación de identidades

`julio` es un LOGIN administrativo local, no la identidad runtime del backend. Para SWV2.1: **backend PostgreSQL runtime role → `capstone_v2_runtime`**; eliminar la dependencia del backend de `julio SUPERUSER` es requisito de SWV2.1.
