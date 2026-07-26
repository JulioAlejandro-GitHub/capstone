# ADR-010: Compatibilidad de adapters heredados

- Estado: Aceptado
- Contexto/problema: scripts/tests/backend aún importan `src.*`.
- Decisión: mantener sin renombrar/eliminar; nuevos módulos importan `malaria_dl`; adapters delegan y no reciben lógica nueva.
- Alternativas: retiro inmediato o duplicación; rechazadas por regresión.
- Positivas: transición segura.
- Negativas: deuda temporal y doble namespace.
- Riesgos/mitigación: dependencia perpetua; regla lint, inventario y tests contract.
- Compatibilidad: CLIs/scripts actuales son gate.
- Revisión futura: cero imports internos, externos migrados, release completo de deprecación.
- Componentes/prompts: todo Python; P2–P15.
