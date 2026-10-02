---
name: testing-audit-guardian
description: Activa este skill al redactar pruebas (Pytest), auditar elegibilidad de Stage 2, o crear/modificar documentación técnica y sus estados.
---

# Testing Contracts & Documentation Guardian

## Summary
Este skill impone rigor en la creación de suites de pruebas asíncronas para FastAPI y garantiza que la gobernanza documental se rija estrictamente por los banners de estado internos, ignorando el sistema de archivos físico[cite: 3].

## When to Use
* Al escribir, analizar o depurar tests en `backend_api/tests/` (Pytest).
* Al evaluar o codificar las reglas de elegibilidad del pipeline de modelos (ej. Stage 2).
* Al redactar, mover, auditar o consultar la documentación en `docs/`[cite: 3].

## Core Rules & Steps
1. **Testing de Contratos (Pytest Asíncrono):**
   * Las pruebas del backend deben aislar transacciones en PostgreSQL para no contaminar la fuente de verdad[cite: 3].
   * Utiliza integraciones asíncronas (`pytest-asyncio`, `httpx.AsyncClient`) para validar los endpoints de FastAPI.
   * La instrucción para ejecutar la suite de pruebas SIEMPRE debe ser a través del Makefile (ej. `make test-backend`, `make validate`)[cite: 3].
2. **Auditoría de Elegibilidad (Pipeline de ML):**
   * Valida como una regla dura del negocio que la elegibilidad para Stage 2 requiere obligatoriamente: `TRAIN completed` + `EVALUATE completed`[cite: 3]. Las pruebas deben afirmar este estado.
3. **Gobernanza Documental Estricta:**
   * La jerarquía y validez de un documento la define **exclusivamente su banner interno** (ej. `CURRENT_DOC`, `LEGACY_REQUIRED`, `HISTORICAL_AUDIT`)[cite: 3]. 
   * La declaración del banner prevalece absolutamente sobre la carpeta o ubicación física del archivo en el directorio[cite: 3].
   * Cualquier nuevo documento o alteración de estado debe quedar indexado en `docs/README.md`[cite: 3].

## Gotchas
* Nunca asumas que un documento es la "versión actual" basándote solo en el nombre del archivo o su ruta; revisa siempre el banner de estado.
* No sugieras ejecutar `pytest` directamente en la consola del host; recuerda que la validación debe pasar por el flujo de orquestación de Docker/Makefile[cite: 3].