# E10.10.5E.1 — resultados

**Baseline/ACL E-01 recertificada. E incompleta y bloqueada por E-02; Gate E no solicitado.**

- PostgreSQL 17.9 nuevo: instalación Alembic, catálogo completo/ownership/ACL, 46 casos server + 45 D-03 + 5 D-05 aprobados. Rollback, idempotencia y backup/restore aprobados.
- Login runtime real: SELECT permitido; INSERT, UPDATE, DELETE, TRUNCATE, ALTER y DROP rechazados. Stamp autenticado rechazado; CLI stamp/upgrade runtime rechazadas antes de conexión por guarda de identidad. PUBLIC sin permisos nuevos.
- Guarda real: v2 y legacy reconocidos; revisión desconocida/ausente/múltiple y error SQL rechazados. Eventos rechazados antes de emitir DML con revisión inválida. Legacy probado con migraciones reales y padres sintéticos en schema desechable.
- 99 pruebas offline baseline/adopción aprobadas; 7 de contrato de revisión/arquitectura aprobadas. Compilación reproducible y validador estático aprobados, 54 archivos históricos preservados. No equivalen a integración completa.
- Continuación E: evento de época aceptado, duplicado reconocido, owner falso rechazado, procedencia ausente rechazada con rollback. Evaluación con contexto sintético explícito: rechazo 23514 por `ck_v2_no_result_json`. Rollback confirmado: ninguna evaluación, métrica ni JSONB final; sólo persiste época previa. Código 2 deliberado.

[Informe reproducible y hashes](e10_10_5e1_acl_resolution.md) · [Certificado](e10_10_5e1_evidence/route_a/certificate.json) · [Resultados SQL E-02](e10_10_5e1_evidence/route_a/e10_projection.json).

No se reejecutaron ni acreditaron como parte de E.1 TRAIN local/Docker, VALIDATION integral, API/React, publicación/linaje ni productores pendientes. Los conteos Python/frontend y build de la etapa E anterior son históricos y están [conservados](e10_10_5e1_evidence/previous_reports/e10_10_5_test_results.md).
