-- DBV2.2 + approved R1. Install exclusively via guarded Alembic v2.
SET LOCAL search_path TO 'public', 'pg_catalog';

SET LOCAL check_function_bodies TO 'true';

CREATE EXTENSION pgcrypto WITH SCHEMA public;

REVOKE ALL PRIVILEGES ON SCHEMA public FROM PUBLIC;

