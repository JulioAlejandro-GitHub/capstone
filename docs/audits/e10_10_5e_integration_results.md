# E10.10.5E — integración incompleta, bloqueada por E-02

**E-01 RESUELTA. BASELINE E.1 RECERTIFICADA. E10.10.5E — INTEGRACIÓN INCOMPLETA. GATE E BLOQUEADO, NO SOLICITADO.**

La autorización E-01 permitió exclusivamente SELECT runtime de la revisión. Se instaló una instancia PostgreSQL 17.9 nueva, se repitió la certificación y se comprobó preflight autenticado runtime, sin migrador como usuario de aplicación ni fallback. [Certificado y comandos](e10_10_5e1_acl_resolution.md).

La continuación autorizada E aceptó una época mediante ResultService/PostgresResultRepository, reconoció duplicado y rechazó fencing inválido. La evaluación sin procedencia revierte. Para diagnosticar la proyección se suministró contexto de fixture explícitamente sintético: la evaluación final falla con **23514 / ck_v2_no_result_json**, porque el adaptador preparado escribe `runs.parameters.training_results` y la baseline lo prohíbe. Ledger de esa evaluación, métricas, evaluación tipada y JSONB final se revierten juntos. [Evidencia SQL](e10_10_5e1_evidence/route_a/e10_projection.json).

Se detuvo E conforme a la regla de nueva incompatibilidad arquitectónica. No se modificó la restricción. [Decisión requerida: destino JSONB en v2](e10_10_5e1_acl_resolution.md#decisión-e-02-requerida).

| Recorrido | Estado actual |
|---|---|
| Baseline, ACL, revisión runtime | Aprobado E.1; 96 casos SQL baseline, rollback/idempotencia/restore |
| Guarda negativa antes de eventos | Aprobada con SQL real; legacy con migraciones reales y padres sintéticos |
| Ledger E10 época/duplicado/fencing | Probado con servicio y runtime real; historial mínimo sintético |
| Evaluación ledger + JSONB + tipadas | Bloqueada E-02; rollback comprobado |
| Producción/sellado de procedencia | Pendiente; fixture no acredita productor |
| TRAIN local y Docker sintético | Pendiente |
| VALIDATION y calibración | Pendiente recorrido integral |
| Fallos SQL/recuperación | Rollback E-02 demostrado; reinicios, ACK y concurrencia pendientes |
| Publicación y linaje | Pendiente |
| API y React | Preparación anterior, no acreditados contra recorrido completo runtime v2 |
| Historial, ensembles, XAI | Productores y recorridos poblados pendientes |

No se solicita Gate E ni se declara integración completada. Sin acceso operativo, cutover, campañas reales, modificación del dataset congelado ni de contratos D-01 a D-06. [Informe anterior preservado](e10_10_5e1_evidence/previous_reports/e10_10_5e_integration_results.md).
