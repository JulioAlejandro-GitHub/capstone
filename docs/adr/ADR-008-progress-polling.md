# ADR-008: Progreso mediante polling HTTP

> **Estado documental:** `LEGACY_REQUIRED` — transporte no materializado.
> **Uso operativo:** No; el flujo vigente ejecuta las etapas síncronamente y no ofrece el
> cursor/polling incremental descrito aquí.
> **Evolución:** conservar como decisión histórica hasta introducir progreso asíncrono o
> sustituirla mediante un ADR nuevo.

- Estado: Aceptado
- Contexto/problema: frontend requiere resultados progresivos.
- Decisión: polling de job y endpoint cells con cursor/updated_after; estados independientes del transporte.
- Alternativas: WebSocket/SSE; diferidas fuera MVP.
- Positivas: simple, recuperable y cacheable.
- Negativas: más requests y latencia.
- Riesgos/mitigación: carga DB; backoff, ETag, cursor e índices.
- Compatibilidad: endpoints actuales no cambian.
- Revisión futura: necesidad medida de latencia/event streaming.
- Componentes/prompts: API/UI/queue; P6/P14.
