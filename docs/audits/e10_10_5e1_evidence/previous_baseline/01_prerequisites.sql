-- E10.10.5A frozen Alembic resource. Execute only through the guarded v2 environment.
SET LOCAL search_path = public, pg_catalog;

SET LOCAL check_function_bodies = true;

CREATE EXTENSION pgcrypto WITH SCHEMA public;

REVOKE ALL ON SCHEMA public FROM PUBLIC;

