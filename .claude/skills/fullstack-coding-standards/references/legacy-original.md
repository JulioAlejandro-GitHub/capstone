# Documento histórico — no normativo

Este texto se conserva para trazabilidad. Las reglas actuales están en `SKILL.md` y las referencias actualizadas.

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

### Frontend: Sistema de diseño UX/UI de Capstone

Al crear, modificar o refactorizar interfaces React/TypeScript destinadas a reportes científicos, aplicar obligatoriamente el contrato **CAPSTONE-UI-TOKENS.1**.

**Fuente de verdad:**
`docs/contracts/capstone_ui_css_policy.md`

**Reglas obligatorias:**

1. **Adopción explícita:** utilizar `.ds-report` como ámbito de aplicación del sistema visual de reportes. No aplicar sus estilos globalmente ni asumir que todas las pantallas ya fueron migradas.

2. **Referencia visual:** conservar el lenguaje visual de la página `/modelo-ia/ejecuciones?datasource=malaria`, que constituye la referencia UX/UI aprobada para los reportes científicos.

3. **Reutilización antes que creación:** antes de agregar estilos o componentes, revisar los tokens, clases, primitivas y componentes React existentes. Priorizar su reutilización y evitar duplicaciones.

4. **Responsabilidades CSS:**
   - `frontend/src/styles/tokens.css`: variables y decisiones visuales.
   - `frontend/src/styles/ds-primitives.css`: primitivas, controles y variantes reutilizables.
   - `frontend/src/styles/report-components.css`: composición y patrones visuales de reportes.
   - `frontend/src/styles/smear-analysis-immersive.css`: estilos exclusivos de Análisis de frotis; no modificar como parte de trabajos de reportes.

5. **Separación de ámbitos:** Análisis de frotis conserva su experiencia visual independiente. Los cambios UX/UI de reportes no deben modificar ni afectar involuntariamente dicha experiencia.

6. **Componentes reutilizables:** los elementos compartidos, incluidos visores científicos, tablas, tarjetas, badges, controles y modales, deben implementar una única presentación reutilizable. Evitar implementaciones visuales paralelas por página.

7. **Consistencia visual:** consumir tokens semánticos para colores, tipografía, espaciados, bordes, estados y dimensiones. No introducir paletas independientes, valores repetidos innecesarios, frameworks CSS adicionales ni uso indiscriminado de `!important`.

8. **Accesibilidad y responsive:** conservar navegación por teclado, foco visible, contraste adecuado, estados explícitos y comportamiento adaptable. En comparaciones científicas, preservar la alineación visual entre elementos comparables.

9. **Adopción progresiva:** los reportes nuevos deben utilizar el sistema de diseño desde su implementación. Los reportes existentes se migrarán gradualmente mediante tareas específicas; no realizar migraciones masivas fuera del alcance solicitado.

10. **Preservación funcional:** los cambios exclusivamente UX/UI no deben modificar APIs, contratos científicos, lógica de negocio, PostgreSQL, rutas ni procesamiento de modelos de IA.

11. **Validación:** ejecutar TypeScript, build y pruebas pertinentes. La equivalencia visual debe comprobarse en navegador; no declararla únicamente por superar pruebas automatizadas.

**Regla de decisión:** antes de crear una clase CSS o componente visual nuevo, comprobar si existe una solución reutilizable documentada en CAPSTONE-UI-TOKENS.1.

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
