---
name: execution-plane-guardian
description: Gobernar ejecución de TRAIN EVALUATE EXPLAIN TEST y campañas en Docker o Python local.
---

# execution-plane-guardian

## Reglas
- Separar plano de control (FastAPI, frontend, PostgreSQL) y plano de ejecución (Docker o Python local/macOS); no asumir un modo sin revisar configuración real.
- PostgreSQL vigente es la fuente de verdad de ejecuciones, métricas y relaciones. Binarios grandes fuera de la BD, referenciados por artefactos.
- Cada ejecución conserva identidad y resultados históricos; nunca sobrescribir intentos anteriores.
- TRAIN, EVALUATE, EXPLAIN y TEST tienen selección y orquestación equivalentes entre CLI de módulo y scripts correspondientes, conforme al código verificado.
- TEST requiere TRAIN con checkpoint; utiliza únicamente split TEST. TRAIN/VALIDATION no deben consumir TEST.
- No imponer EVALUATE ni EXPLAIN como prerrequisito de TEST.

## Referencias
- `references/runtime-topology.md`
- `references/execution-scientific-lineage.md`
- `references/legacy-execution-plane.md` y `references/legacy-hybrid-runtime.md` (históricos; no normativos).
