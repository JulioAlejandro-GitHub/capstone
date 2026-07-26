# ADR-007: Inferencia multimodelo paralela

- Estado: Aceptado
- Contexto/problema: se requieren uno o varios modelos autorizados.
- Decisión: assignments congelados con role primary/additional/comparison; una predicción por crop/model/run; resultados paralelos; no ensemble automático.
- Alternativas: un solo modelo o ensemble implícito; rechazadas por requisito y pérdida de identidad.
- Positivas: comparación transparente.
- Negativas: costo y resultados potencialmente discordantes.
- Riesgos/mitigación: confusión UX; etiquetar modelo/role/error y no fusionar.
- Compatibilidad: default conserva inferencia simple.
- Revisión futura: ensemble sólo con evaluación/calibración propia y nuevo ADR.
- Componentes/prompts: governance/classifier/aggregate/UI; P10/P11/P14.
