# ADR-015: Salida científica no diagnóstica

- Estado: Aceptado
- Contexto/problema: “Productivo” y labels pueden interpretarse clínicamente.
- Decisión: producto y contratos usan región candidata, sospecha algorítmica, probabilidad estimada, revisión requerida y resultado experimental. Prohibidos paciente positivo/negativo y diagnóstico automático.
- Alternativas: terminología clínica directa; rechazada por ausencia de validación/certificación.
- Positivas: alcance honesto y menor riesgo.
- Negativas: requiere disciplina UX/report/API.
- Riesgos/mitigación: uso indebido; disclaimers, RBAC, audits y review.
- Compatibilidad: mapping técnico parasitized/uninfected permanece; su presentación incluye contexto experimental.
- Revisión futura: sólo proceso regulatorio formal, fuera MVP.
- Componentes/prompts: API/UI/report/agents; todos.
