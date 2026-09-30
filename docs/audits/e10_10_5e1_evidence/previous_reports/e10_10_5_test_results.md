# E10.10.5E — resultados parciales

**E BLOQUEADA EN PREFLIGHT RUNTIME; NO APROBADA.** Gate D fue aprobado por el usuario.

- PostgreSQL 17.9 nuevo y aislado: instalación Alembic D.4 correcta; manifiesto exacto.
- Runtime: fallo real `permission denied for table alembic_version`, convertido en `E10_SCHEMA_NOT_READY`. Probe reproducible retorna 2. No aceptación ficticia ni fallback al migrador.
- 265 pruebas Python únicas aprobadas (142 servicio/emisor/ciencia/arquitectura, 121 baseline/adopción/revisiones/API, 2 DTO).
- 201 pruebas frontend aprobadas, incluidas 2 de renderizado React real; build TypeScript/Vite correcto.
- 54 archivos históricos y recursos SQL de baseline sin diferencias. `git diff --check` correcto.
- Pendientes: TRAIN local/Docker integral, fixtures E10 pobladas, rollback SQL y commit, recuperación, fencing concurrente v2, publicación, linaje, XAI y API contra runtime v2. No se acredita cobertura porcentual ni validación clínica.

[Comandos](e10_10_5e_evidence/command_results.json) · [Matriz y límites](e10_10_5e_integration_results.md) · [Resultados D.4 conservados](e10_10_5e_evidence/previous_reports/e10_10_5_test_results.md).
