# ADR-014: Política de explicabilidad

- Estado: Aceptado
- Contexto/problema: Grad-CAM/LIME/SHAP existen batch pero no ligados a cada prediction.
- Decisión: Grad-CAM automático por célula/modelo salvo limitación registrada; LIME/SHAP priority/on-demand; resultado enlazado a prediction exacta; fallos no destructivos.
- Alternativas: todo automático o XAI global; rechazadas por costo/trazabilidad.
- Positivas: evidencia comparable.
- Negativas: costo Grad-CAM y artifacts.
- Riesgos/mitigación: saturación/causalidad aparente; budget, states, disclaimer y contexto original.
- Compatibilidad: adapters reutilizan implementaciones actuales.
- Revisión futura: profiling y evaluación de utilidad.
- Componentes/prompts: XAI/queue/UI; P12/P14.
