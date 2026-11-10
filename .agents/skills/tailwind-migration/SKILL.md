---
name: tailwind-migration
description: >
  Migra un subsistema frontend existente a una nueva carpeta usando exclusivamente
  Tailwind CSS. Genera un mapa de migración (inventario, orden, tracking) y ejecuta
  la migración componente por componente. Úsalo cuando el usuario pida migrar
  estilos a Tailwind, crear un frontend2, o replicar un frontend con Tailwind.
---

# Tailwind Migration Skill

## Contrato

- Objetivo: replicar `frontend/` → `frontend2/` con Tailwind CSS.
- Ámbito: solo la capa de presentación cambia.
- Fuera de ámbito: lógica, routing, API, estado, nombres, estructura de carpetas.
- Si un archivo no tiene estilos → se copia tal cual.
- Si algo es ambiguo → preguntar, no asumir.

## Restricciones

- NO refactors. Si el código original es feo, replicalo feo.
- NO inventes componentes, rutas ni servicios que no existan en `frontend/`.
- NO optimices performance, no agregues memoización, no cambies patterns.
- NO modifiques `frontend/` en ningún momento.
- NO continúes a la siguiente onda sin que el usuario lo pida.

## Reglas inmutables

1. `frontend/` es **solo lectura**.
2. `frontend2/` replica la estructura **completa** de `frontend/` (routing, hooks, services, utils, tipos, state, config, tests).
3. La única diferencia permitida es la capa de estilos: Tailwind CSS exclusivamente.
4. Prohibido: CSS-in-JS, CSS Modules, SASS, LESS, MUI, Chakra, o cualquier librería que inyecte estilos.

## Fase 1 — Análisis e inventario

1. Explora `frontend/` completo (no solo componentes con estilos).
2. Genera `frontend2/MIGRATION_MAP.md` con:
   - Estructura de carpetas anotada.
   - Tabla de componentes: `Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado`
   - Design tokens → propuesta de `@theme`
   - Casos especiales (estilos dinámicos, keyframes, selectores complejos)
   - Orden de migración por ondas
   - Bloque de tracking: `Total | Migrados | Pendientes | Bloqueados | %`
3. **DETENTE.** Reportá el inventario y esperá confirmación para migrar.

## Fase 2 — Migración

Sigue el orden de `MIGRATION_MAP.md`. **Una onda por turno.**

### Onda 0 — Base (sin estilos)
- Tipos, utils, services, hooks, config, state management.
- Se copian **tal cual** a `frontend2/` (solo ajustar paths de import).
- No se aplica Tailwind aquí.

### Onda 1+ — UI
- Primitivas → features → layouts/páginas.
- Para cada componente:
  1. Lee el original en `frontend/`.
  2. Crea el equivalente en `frontend2/` con la misma lógica.
  3. Reemplaza estilos por utilities de Tailwind:
     - Estados → `hover:`, `focus:`, `active:`, `disabled:`
     - Responsive → `sm:`, `md:`, `lg:`, `xl:`
     - Valores dinámicos → `style={{ '--x': val }}` + `bg-[var(--x)]`
     - Librerías con estilos → componente propio con Tailwind
  4. Elimina imports de estilos del componente migrado.
  5. Actualiza `MIGRATION_MAP.md`: ⬜→✅, % y log.

### Checkpoint al final de cada onda

- **DETENTE.**
- Reportá: qué migraste, decisiones de mapeo, siguiente onda pendiente.
- Esperá que el usuario diga "continuar" antes de avanzar.

## Fase 3 — Verificación final

- `frontend2/` compila sin errores.
- No hay archivos `.css` con reglas propias (solo `@import "tailwindcss"` + `@theme`).
- No hay imports de librerías de estilos.
- `frontend/` no ha sido modificado (verificar con `git diff frontend/`).
- `MIGRATION_MAP.md` muestra 100% completado.

## Salida por componente

Para cada migración, reporta:
- Ruta fuente → ruta destino
- Decisiones de mapeo no triviales (solo si aplica)   