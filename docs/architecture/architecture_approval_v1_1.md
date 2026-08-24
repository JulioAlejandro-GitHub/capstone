# Acta de aprobación — Architecture Baseline v1.1

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No; conserva la aprobación de la arquitectura objetivo v1.1.
> **Snapshot:** Entrega 2, previo a la implementación incremental de Prompts 2–8.

## Identificación

- Baseline: `delivery2_architecture_baseline_v1_1.md`
- Snapshot de código: `3c79bb08a36f210c58d7076cf58111d4de554752`
- Migración real más reciente verificada: 029
- Naturaleza: diseño aprobado; sin implementación

## Checklist formal

### Arquitectura

- [x] Estado actual, objetivo, transición y fuera de alcance diferenciados.
- [x] Monolito modular, FastAPI, React, PostgreSQL y filesystem formalizados.
- [x] QC rejected termina antes de job/detection.
- [x] Detector y classifier separados.
- [x] Queue PostgreSQL con claim/lease/retry/recovery/cancel/idempotency.
- [x] Polling HTTP y cells incremental definidos.
- [x] `StorageProvider`/`LocalStorageProvider` definidos.

### Gobierno

- [x] Publicaciones = catálogo multi-modelo.
- [x] `stage2/default` = único default por contexto.
- [x] Default sólo apunta a publicación activa.
- [x] Desactivación en uso se rechaza.
- [x] Rollback crea nueva revisión de slot.
- [x] Multimodelo paralelo, sin ensemble.

### Datos y contratos

- [x] Modelo conceptual completo y tabla legacy `predictions` no sobrecargada.
- [x] Diez máquinas de estados separadas.
- [x] Coordenadas `pixel_xywh_top_left_v1`.
- [x] Detector, crop, classification, XAI, aggregate y review definidos.
- [x] Auto/human y revisiones separados.
- [x] Report/artifacts versionados y checksums obligatorios.
- [x] Trece JSON Schemas y OpenAPI draft creados.

### Seguridad y ciencia

- [x] Auth académica y cinco roles.
- [x] Permisos y acciones sensibles auditables.
- [x] Linaje y reproducibilidad end-to-end.
- [x] Lenguaje experimental no diagnóstico.
- [x] Split por patient_id obligatorio.
- [x] Fallos parciales y denominadores explícitos.

### Integridad

- [x] Quince ADR existen y están aceptados.
- [x] No se cambió código productivo.
- [x] No se cambió SQL/migraciones/PostgreSQL.
- [x] No se descargaron datos/modelos.
- [x] No se entrenó/publicó/cambió default.
- [x] No se eliminó documentación/adapters.

## Decisión

**APROBAR Architecture Baseline v1.1 para iniciar Prompt 2.**

La aprobación no autoriza implementar el pipeline completo. Prompt 2 debe limitarse a foundation: configuración, estrategia de migraciones, seguridad base, logging/correlation, estructura modular, pruebas y herramientas de ingeniería conforme a ADR.

## Bloqueantes de entrada a Prompt 2

No quedan decisiones estructurales abiertas. Antes de mutar código/DB, Prompt 2 debe confirmar:

1. entorno PostgreSQL efímero para tests;
2. estrategia de baseline de migraciones sin reescribir 001–029;
3. versión Python soportada para API/worker;
4. política local de secretos;
5. identidad del responsable que aprueba cambios de RBAC/schema.

Estos son gates de ejecución, no reapertura de arquitectura.
