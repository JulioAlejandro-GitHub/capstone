---
name: tailwind-migration
description: >
  Migra un subsistema frontend existente a una nueva carpeta usando exclusivamente
  Tailwind CSS. Genera un mapa de migración (inventario, orden, tracking) y ejecuta
  la migración componente por componente. Úsalo cuando el usuario pida migrar
  estilos a Tailwind, crear un frontend2, o replicar un frontend con Tailwind.
---

# Tailwind Migration Skill

## Reglas inmutables

1. El subsistema fuente (`frontend/`) es **solo lectura**. Nunca lo modifiques.
2. El destino (`frontend2/`) usa **únicamente Tailwind CSS** para presentación.
3. La lógica (estado, routing, API, hooks) se replica idéntica. Solo cambia la capa visual.
4. Prohíbe: CSS-in-JS, CSS Modules, SASS, LESS, MUI, Chakra, o cualquier librería con estilos propios.

## Fase 1 — Análisis e inventario

1. Explora `frontend/` (árbol de carpetas, rutas, dependencias, design tokens).
2. Genera `frontend2/MIGRATION_MAP.md` con:
   - Tabla de componentes: `Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado`
   - Design tokens → propuesta de `@theme`
   - Casos especiales (estilos dinámicos, keyframes, selectores complejos)
   - Orden de migración por ondas (primitivas → features → layouts/páginas)
   - Bloque de tracking: `Total | Migrados | Pendientes | Bloqueados | %`

## Fase 2 — Migración

Sigue el orden de `MIGRATION_MAP.md`. Para cada componente:

1. Lee el original en `frontend/`.
2. Crea el equivalente en `frontend2/` con la misma lógica.
3. Reemplaza estilos por utilities de Tailwind:
   - Estados → `hover:`, `focus:`, `active:`, `disabled:`
   - Responsive → `sm:`, `md:`, `lg:`, `xl:`
   - Valores dinámicos → `style={{ '--x': val }}` + `bg-[var(--x)]`
   - Librerías con estilos → componente propio con Tailwind
4. Elimina imports de estilos del componente migrado.
5. Actualiza `MIGRATION_MAP.md`: cambia estado ⬜→✅, actualiza % y log.

## Fase 3 — Verificación

- `frontend2/` compila sin errores.
- No hay archivos `.css` con reglas propias (solo `@import "tailwindcss"` + `@theme`).
- No hay imports de librerías de estilos.
- `frontend/` no ha sido modificado.

## Salida por componente

Para cada migración, reporta:
- Ruta fuente → ruta destino
- Decisiones de mapeo no triviales (solo si aplica)   