# ADR-014: Política de explicabilidad

> **Estado documental:** `LEGACY_REQUIRED` — sustituido para clasificación celular.
> **Uso operativo:** Sólo como antecedente; no autoriza generación automática o masiva.
> **Sustitución:** ADR-020 exige Grad-CAM manual, unitario, on-demand y retry explícito.

- Estado: Aceptado
- Contexto/problema: Grad-CAM/LIME/SHAP existen batch pero no ligados a cada prediction.
- Decisión histórica general: Grad-CAM automático por célula/modelo salvo
  limitación registrada; LIME/SHAP priority/on-demand; resultado enlazado a
  prediction exacta; fallos no destructivos.
- Sustitución para Prompt 8: ADR-020 prevalece para la clasificación celular
  implementada. Grad-CAM es exclusivamente manual, unitario y on-demand; no hay
  generación masiva ni automática, y el retry requiere acción explícita.
- Alternativas: todo automático o XAI global; rechazadas por costo/trazabilidad.
- Positivas: evidencia comparable.
- Negativas: costo Grad-CAM y artifacts.
- Riesgos/mitigación: saturación/causalidad aparente; budget, states, disclaimer y contexto original.
- Compatibilidad: adapters reutilizan implementaciones actuales.
- Revisión futura: profiling y evaluación de utilidad.
- Componentes/prompts: XAI/queue/UI; P12/P14.
