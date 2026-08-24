# ADR-005: Quality gate terminal antes del job

> **Estado documental:** `LEGACY_REQUIRED` — sustituido parcialmente.
> **Uso operativo:** No como secuencia literal; el sistema crea el analysis run y luego
> ejecuta su quality gate antes de detección/clasificación.
> **Sustitución:** ADR-018 y `docs/architecture/microscopy_quality_gate.md`.

- Estado: Aceptado
- Contexto/problema: QC actual sólo advierte y no bloquea.
- Decisión: upload crea original y assessment; rejected conserva ambos, informa motivos y no crea `analysis_job`.
- Alternativas: QC dentro del job o warning-only; rechazadas por responsabilidad y costo.
- Positivas: rechazo inmediato y pipeline limpio.
- Negativas: command de QC separado.
- Riesgos/mitigación: falsos rechazos; policy versionada, revisión y nueva evaluación sin mutar anterior.
- Compatibilidad: `check_image_quality()` se reutiliza como primitive, no como policy completa.
- Revisión futura: evidencia científica cambia reglas.
- Componentes/prompts: ingest/QC/UI; P4/P5/P14.
