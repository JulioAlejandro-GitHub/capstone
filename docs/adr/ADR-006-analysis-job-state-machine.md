# ADR-006: Máquina de estados de analysis job

> **Estado documental:** `LEGACY_REQUIRED` — máquina objetivo no materializada.
> **Uso operativo:** No; los estados actuales están definidos por los runs de calidad,
> detección y clasificación especializados.
> **Sustitución:** ADR-018, ADR-019, ADR-020 y sus constraints Alembic.

- Estado: Aceptado
- Contexto/problema: estados legacy no representan stages/leases.
- Decisión: created, queued, claimed, detecting, cropping, classifying, explaining, aggregating y terminales completed/partial_failure/failed/cancelling/cancelled. QC queda fuera.
- Alternativas: estado único running o incluir QC; rechazadas por ambigüedad.
- Positivas: progreso, recovery y fallos claros.
- Negativas: más transiciones/eventos.
- Riesgos/mitigación: transiciones inválidas; servicio único, checks y event ledger.
- Compatibilidad: mapear legacy pending/running/completed a read model.
- Revisión futura: stages nuevos sin cambiar semántica terminal.
- Componentes/prompts: queue/orchestrator/API/UI; P3/P6/P14.
