# E10.10.5E — riesgos actuales

**E-01 resuelta. E-02 bloqueante. Gate E continúa bloqueado y no solicitado.**

- **E-02:** la restricción certificada `ck_v2_no_result_json` contradice escribir `runs.parameters.training_results` junto a ledger y métricas. Reproducido con runtime real, SQLSTATE 23514, rollback completo. Requiere decisión antes de continuar E; no está autorizado cambiar esa restricción por E-01.
- Procedencia de checkpoint/protocolo/población aún sin productor y sellado integral. El contexto del probe es exclusivamente sintético y no acredita TRAIN.
- Pendientes TRAIN local/Docker, VALIDATION/calibración, recuperación/reinicio/ACK, concurrencia, publicación/linaje, API/React y productores de historial/ensembles/XAI.
- Lectores anteriores de resumen/detalle todavía necesitan adaptación v2 para evitar fallback científico y preservar métricas indefinidas como NULL.
- La nueva referencia de baseline es E.1. D.4 y su Route B son evidencia histórica; no se declara una adopción Route B nueva ni se autoriza cutover.
- Certificado ACL y pruebas offline no acreditan integración E ni validación clínica. Sin acceso operativo, campañas reales, dataset modificado ni hashes E10 históricos alterados.

[Decisión concreta E-02 y evidencia](e10_10_5e1_acl_resolution.md).
