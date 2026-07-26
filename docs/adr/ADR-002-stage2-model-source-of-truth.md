# ADR-002: Fuente de verdad de modelos Etapa 2

- Estado: Aceptado
- Contexto/problema: publicaciones y deployments actuales pueden divergir.
- Decisión: `stage2_model_publications` es catálogo multi-modelo autorizado; `stage2/default` es el único default por contexto y debe referenciar una publicación activa. Desactivar una publicación en uso retorna conflicto hasta reasignar/desactivar el slot. Rollback cambia la revisión del slot.
- Alternativas: publicación única, checkpoint directo o desactivación automática; rechazadas por trazabilidad/ambigüedad.
- Positivas: selección determinista y catálogo flexible.
- Negativas: relación/transacción adicional.
- Riesgos/mitigación: drift; FK/servicio transaccional y validación en inferencia.
- Compatibilidad: adapters para endpoints actuales.
- Revisión futura: necesidad real de múltiples defaults por contexto formalizado.
- Componentes/prompts: governance/API/classifier; P3/P10.
