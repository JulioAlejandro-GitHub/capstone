---
name: fullstack-coding-standards
description: Activa este skill al refactorizar, revisar o escribir nuevo código para el Frontend (React/TypeScript) o el Backend (FastAPI/Python).
---

# Fullstack Coding Standards Guardian

## Summary
Este skill impone estándares estrictos de Clean Code, tipado fuerte y separación de responsabilidades tanto para el ecosistema React + Vite como para FastAPI.

## When to Use
* Al crear nuevos componentes de React, hooks o funciones en el frontend.
* Al escribir servicios, rutas o lógica de negocio en el backend.
* Al refactorizar código existente o realizar *code reviews*.

## Core Rules & Steps

### 1. Frontend: React + TypeScript (Vite)
* **Tipado Estricto:** El uso de `any` está estrictamente prohibido. Define `Interfaces` o `Types` claros para todas las props, estados y respuestas de API.
* **Separación UI / Lógica:** Los componentes visuales no deben contener lógica de negocio compleja ni llamadas directas con `fetch`/`axios`. Extrae la lógica a Custom Hooks (ej. `useCampaigns`) o a una capa de servicios de API.
* **Rendimiento:** Evita re-renderizados innecesarios usando `useMemo` y `useCallback` solo cuando las operaciones sean costosas. Desacopla estados que mutan rápidamente de la jerarquía principal del DOM.

### 2. Backend: FastAPI + Python
* **Type Hinting Obligatorio:** Toda función, ruta y método DEBE tener anotaciones de tipo completas en sus parámetros y valores de retorno (`-> Type`).
* **Inyección de Dependencias:** No instancies clases de servicio o conexiones a base de datos dentro de las funciones. Usa siempre `Depends()` de FastAPI para inyectar repositorios y servicios.
* **Manejo de Excepciones:** No uses bloques `try/except` masivos que oculten errores. Lanza excepciones HTTP específicas (`HTTPException`) en la capa de servicios o centraliza los errores con *Exception Handlers* globales.

### 3. Principios Generales (Clean Code)
* **Responsabilidad Única (SRP):** Las funciones y componentes deben ser cortos y hacer exactamente una cosa. Si una función requiere usar "Y" en su descripción (ej. `validate_and_save`), sepárala en dos.
* **Nombres Descriptivos:** Nombra variables, funciones y clases revelando su intención (ej. `get_active_campaigns()` en lugar de `get_data()`).
* **Cero Código Muerto:** No comentes código para "usarlo después". Bórralo (Git ya mantiene el historial). El código debe explicarse a sí mismo; usa comentarios solo para explicar el *por qué*, no el *qué*.

## Gotchas
* Si estás en el frontend, asegúrate de no filtrar claves secretas ni variables de entorno no públicas (usa el prefijo `VITE_` solo cuando sea estrictamente necesario).
* Al hacer validaciones de datos, apóyate siempre en Pydantic (Backend) y schemas de Zod/Yup (Frontend) en lugar de validaciones manuales con múltiples `if`.