# ADR-012: Política de fallos parciales

- Estado: Aceptado
- Contexto/problema: pipeline fan-out puede fallar por célula/modelo/XAI.
- Decisión: detector total falla job; crop/cell/model continúan y pueden cerrar partial; XAI no invalida prediction; aggregator retryable conserva inputs; report no cambia analysis.
- Alternativas: all-or-nothing o ocultar fallos; rechazadas por costo/trazabilidad.
- Positivas: máxima evidencia útil.
- Negativas: resultados parciales requieren denominadores/UX.
- Riesgos/mitigación: interpretar parcial como completo; status, counts y warnings obligatorios.
- Compatibilidad: estados terminales nuevos se adaptan a UI legacy.
- Revisión futura: políticas por stage versionadas.
- Componentes/prompts: orchestrator/all stages; P6–P15.
