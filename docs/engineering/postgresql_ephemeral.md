# PostgreSQL efímero — SUPERSEDED

> **Estado documental:** `OBSOLETE_DOC` / `SUPERSEDED`
> **Uso operativo:** No; no iniciar ni destruir PostgreSQL desde esta guía.
> **Sustitución:** `postgresql_local_single_instance.md` y `test_environment.md`.

Esta política histórica fue reemplazada por
[PostgreSQL local: instancia única](postgresql_local_single_instance.md). No se inicia ni
destruye PostgreSQL mediante Docker; los tests locales se aíslan con rollback.
