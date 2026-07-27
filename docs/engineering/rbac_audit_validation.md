# Validación RBAC y auditoría

Estado 2026-07-27: RBAC PASS; rollback por restricción PostgreSQL real PASS para la unidad
compartida; cobertura E2E por cada familia crítica BLOCKED. No se modificó stage2/default.

|Control|Resultado|
|---|---|
|Inventario completo de mutaciones|PASS, 21 rutas incluyendo login|
|Política central en toda mutación legacy|PASS estático, test automático|
|read_only sin escrituras|PASS unitario|
|Publicación sólo administrator|PASS unitario|
|Deployments sólo administrator|PASS unitario|
|Inferencia operator/researcher/admin|PASS unitario|
|401/403 HTTP|PASS para contrato existente; E2E PG BLOCKED|
|`audit_events` append-only|PASS por migración; runtime BLOCKED|
|Login success/failure auditado|PASS por código; runtime BLOCKED|
|Usuario deshabilitado invalida JWT existente|PASS por código; runtime BLOCKED|

La dependencia auditada comprueba el store antes de ejecutar y registra outcome después.
Los servicios legacy abren sus propias transacciones; por tanto el evento genérico y la
mutación no son atómicos. No se afirma lo contrario. La migración crea trigger append-only
y usa `ON DELETE RESTRICT` para actor.
