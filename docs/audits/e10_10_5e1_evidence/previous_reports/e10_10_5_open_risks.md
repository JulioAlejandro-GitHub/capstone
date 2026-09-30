# E10.10.5E — riesgos y bloqueo

Gate D aprobado explícitamente. E iniciada; **integración incompleta, Gate E no solicitado**.

- **E-01 bloqueante:** la ACL D.4 impide leer `alembic_version` con runtime. Debe decidirse si se autoriza una corrección limitada y recertificación aislada. Ninguna modificación de ACL aplicada.
- Proyección preparada requiere procedencia explícita del checkpoint, protocolo, población y contrato de entrada; su producción y sellado desde TRAIN siguen pendientes. No se inventarán hashes ni identidades.
- Faltan productores tipados de historial/ensemble/XAI y acreditación de las diez entidades pobladas, cardinalidades y linaje.
- Lectores anteriores de resumen/detalle todavía necesitan adaptación v2: el nuevo endpoint/panel no elimina sus fallbacks legacy. No está demostrado que todo el frontend preserve nulls en todas las rutas.
- Falta recorrido completo local/HTTP/Docker → ResultService → PostgreSQL v2 → API → React, fallos SQL, recuperación, concurrencia, publicación y linaje EVALUATE/EXPLAIN.
- Pruebas offline/SSR y build aprobados no equivalen a integración SQL ni validación clínica. Sin TEST, campañas reales, dataset regenerado, stamp operativo o cutover.
- Conservar volumen y credenciales privados del entorno E para reproducir el bloqueo; la baseline y evidencia D.4 permanecen intactas.

[Informe y decisión](e10_10_5e_integration_results.md) · [Riesgos D.4 conservados](e10_10_5e_evidence/previous_reports/e10_10_5_open_risks.md).
