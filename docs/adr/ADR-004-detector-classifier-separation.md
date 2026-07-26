# ADR-004: Separación detector-clasificador

- Estado: Aceptado
- Contexto/problema: no existe detector; el clasificador actual opera crops.
- Decisión: `CellDetector` sólo localiza regiones candidatas; `CellClassifier` clasifica crops. RBCNet es un adapter detector, nunca clasificador/XAI/agregador.
- Alternativas: pipeline monolítico o clasificar imagen completa; rechazadas por contrato científico.
- Positivas: componentes evaluables e intercambiables.
- Negativas: más stages/provenance.
- Riesgos/mitigación: coordenadas incompatibles; ADR-011 y contract tests.
- Compatibilidad: clasificador Etapa 1 se reutiliza mediante adapter.
- Revisión futura: detector multi-task validado que conserve interfaces.
- Componentes/prompts: detection/crop/classification; P8–P10.
