# ADR-009: Separación de resultados automáticos y humanos

- Estado: Aceptado
- Contexto/problema: campos planos de review podrían sobrescribir historia.
- Decisión: predictions automáticas inmutables; expert reviews/annotations append-only con supersedes y before/after.
- Alternativas: UPDATE de prediction o una etiqueta final; rechazadas por trazabilidad.
- Positivas: auditoría y comparación.
- Negativas: consultas más complejas.
- Riesgos/mitigación: UI confusa; vistas separadas y etiquetas explícitas.
- Compatibilidad: campos legacy se leen, nuevas escrituras usan tablas especializadas.
- Revisión futura: workflow de consenso, sin mutar historia.
- Componentes/prompts: DB/review/report; P3/P13/P15.
