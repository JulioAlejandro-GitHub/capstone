---
name: fastapi-architecture-guardian
description: Activa este skill cuando se discuta código de backend, FastAPI, endpoints, rutas, servicios, repositorios, validación con Pydantic o la trazabilidad jerárquica de datos médicos.
---

# FastAPI Architecture & Lineage Guardian

## Summary
Este skill impone una arquitectura estricta de 3 capas en FastAPI y asegura que toda la lógica de negocio respete la trazabilidad jerárquica médica inmutable (Caso -> Muestra -> Frotis -> Imagen)[cite: 3].

## When to Use
* Al crear o modificar endpoints en `backend_api/app/routes/`[cite: 3].
* Al implementar lógica de negocio en `backend_api/app/services/`[cite: 3].
* Al realizar consultas a la base de datos en `backend_api/app/repositories/`[cite: 3].
* Al definir esquemas de validación Pydantic en `backend_api/app/schemas/`[cite: 3].

## Core Principles & Steps
1. **Arquitectura de 3 Capas Inquebrantable:**
   * **Rutas (`routes/`):** NUNCA contienen lógica de negocio ni consultas directas a la base de datos[cite: 3]. Su única responsabilidad es recibir la petición, inyectar dependencias, llamar a la capa de servicio y devolver una respuesta Pydantic validada.
   * **Servicios (`services/`):** Contienen TODA la lógica de negocio y la validación de reglas de dominio[cite: 3]. Llaman a los repositorios para obtener o guardar datos. No dependen de objetos HTTP de FastAPI (como `Request` o `Response`).
   * **Repositorios (`repositories/`):** Son la ÚNICA capa que interactúa con SQLAlchemy[cite: 3]. No contienen lógica de negocio.
2. **Jerarquía Médica Sagrada (Trazabilidad):**
   * Todo código que genere o manipule entidades hijas DEBE mantener y validar la trazabilidad estricta: `caso → muestra → frotis → imagen`[cite: 3].
   * Un error en la cadena de trazabilidad debe resultar en un error `400 Bad Request` o `404 Not Found`.
3. **Validación de Etapas del Pipeline:**
   * Al procesar datos de una imagen, el servicio DEBE respetar el pipeline de evaluación: `quality gate → detección → clasificación → revisión humana`[cite: 3].
   * Las etapas son secuenciales; bloquea cualquier intento de saltar una validación previa (ej. clasificar sin pasar el quality gate)[cite: 3].
4. **Respuesta Tipada:** Todos los endpoints deben tener `response_model` declarado explícitamente usando esquemas Pydantic y documentados correctamente en OpenAPI[cite: 3].

## Gotchas
* No uses variables globales para mantener estado. Utiliza siempre la inyección de dependencias (`Depends`) de FastAPI.
* Evita la fuga de modelos ORM (SQLAlchemy) hacia la respuesta JSON. Asegúrate de parsearlos y retornar exclusivamente objetos Pydantic en la capa de rutas.