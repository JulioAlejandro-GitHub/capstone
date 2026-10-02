# Sistema de Diseño Unificado y Tokens Centralizados — Propuesta

**Alcance:** `frontend/` (React 19 + Vite, CSS plano).
**Fecha:** 2026-10-01.
**Estado:** propuesta. No hay cambios de código asociados todavía.

---

## 0. Punto de partida: qué hay realmente en el repositorio

Antes de proponer, conviene corregir una premisa: **el frontend no usa Tailwind CSS**. No hay `tailwind.config.*` ni dependencia en `package.json`. Todo el estilo vive en CSS plano global:

| Archivo | Líneas | Cómo se carga |
|---|---:|---|
| `src/styles.css` | 8.504 | `main.tsx` (global) |
| `src/styles/smear-analysis-immersive.css` | 2.631 | `main.tsx` (global) |
| `src/styles/report-components.css` | 1.436 | solo desde `pages/Runs.tsx` |
| `src/components/ConfusionMatrix.css` | 173 | desde el componente |

Por eso esta propuesta usa **CSS Custom Properties** (`tokens.css`) como fuente única de verdad. Es la opción de menor riesgo y no cambia el build. En la sección 2.7 se explica cómo un eventual Tailwind consumiría estos mismos tokens sin duplicarlos.

### Medición de la deuda visual (los 4 CSS sumados)

| Dimensión | Valores distintos hoy | Objetivo |
|---|---:|---:|
| Colores hex | **467** | ~40 primitivos + ~35 semánticos |
| Colores `rgba()` | **193** | derivados de tokens |
| `font-size` | **49** (de 7px a `clamp(...)`) | 7 pasos |
| `font-weight` | **18** (580, 680, 690, 710, 720, 730, 750…) | 4 |
| `padding` | **137** | escala de 9 pasos |
| `gap` | **46** | la misma escala |
| `border-radius` | **20** (4 a 24px) | 4 |
| `box-shadow` | **49** | 3 niveles por superficie |
| `@media` breakpoints | **~20** anchos distintos (420…1799px) | 4 |
| `!important` | 46 | 0 nuevos |

Los tamaños de 7px, 8px y 9px aparecen **59 veces**. En un panel que un analista lee durante horas, eso es un problema de legibilidad y accesibilidad, no solo de estética.

Ya existe un embrión de tokens: `:root` en `styles.css` define una paleta oscura tipo Material (`--color-background`, `--color-surface-*`, `--color-primary`…). Pero:

- **El shell claro no la usa.** `:root` declara `background: #f6f7fb; color: #172033` en duro, y `.app-shell` repite `#f6f7fb`. La paleta oscura solo la consumen la barra lateral y el análisis de frotis. La dualidad claro/oscuro existe, pero nadie la nombra.
- **La paleta del frotis está declarada tres veces** en `smear-analysis-immersive.css` (líneas ~31, ~173 y ~2389), con el mismo `rgba(11, 19, 38, .74)` copiado a mano.
- **Hay prefijos de token paralelos** (`--smear-*`, `--cell-*`, `--workflow-*`, `--setup-*`, `--sidebar-*`, `--stage2-production-*`) que son alias de alias, sin una capa semántica común.
- **`report-components.css` se importa solo en `Runs.tsx`**, pero estiliza `.campaign-field .toggle` del formulario de campañas. Hoy funciona porque `App.tsx` importa `Runs` de forma estática. Si esa página pasa a `lazy()`, el toggle de campañas pierde su estilo sin que nadie lo note.

> **Restricción crítica para la migración:** 10 archivos de `frontend/tests/*.test.mjs` leen los `.css` como texto y verifican selectores, nombres de tokens y valores literales. Por ejemplo: `--sidebar-expanded-width`, `--stage2-production-*`, `.app-content--smear-workflow[^}]*background:\s*var\(--color-background\)`, `@keyframes smear-scan` y `@media (max-width: 720px)`. Cualquier refactor debe **conservar esos nombres y ubicaciones** o actualizar el test en el mismo commit, de forma explícita.

---

## 1. Auditoría conceptual

### 1.1 El abuso de contenedores anidados

Un contenedor con borde, radio, fondo y sombra le dice al usuario: *"esto es un objeto independiente"*. Cuando se anidan varios, cada nivel compite por esa misma señal y la jerarquía se aplana: todo parece igual de importante.

**Caso concreto: `pages/CampaignConfiguration.tsx`.** En la sección «4. Configuración de modelos» se apilan estas cajas con borde:

```
.panel                      border #e3e7f0 · radius 18px · shadow 0 12px 30px · padding 20px
└─ .campaign-variant        border #e3e7f0 · radius 14px · padding 14px
   └─ .campaign-model-config   border #e3e7f0 · radius 12px · padding 10px 14px   (<details>)
      └─ .campaign-parameter-group  border #eef1f6 · radius 10px · padding 10px 12px 14px (<fieldset>)
         └─ .campaign-check / inputs  border #e3e7f0 · radius 12px · padding 10px 12px
```

Hay **cinco bordes concéntricos con cinco radios distintos** (18 → 14 → 12 → 10 → 12). Consecuencias medibles:

1. **Pérdida de ancho útil.** El padding acumulado por lado es 20 + 14 + 14 + 12 = 60px; en ambos lados son ~120px de "marco" antes del primer input. En la columna principal (`minmax(0,1fr)` junto a un aside de 320px), eso empuja la grilla `auto-fill, minmax(210px,1fr)` de tres columnas a dos en pantallas de portátil.
2. **Ruido de bordes.** Cada línea gris de 1px es un trazo que el ojo procesa. Con cinco niveles, el usuario ve marcos en vez de datos.
3. **Radios que no encajan.** Un radio interior que no sea `radio_exterior − padding` produce esquinas que "bailan". Con valores arbitrarios es imposible lograrlo.
4. **El estilo se cuela en el JSX.** Aparecen `style={{ marginTop: '24px' }}` y `borderTop: '1px solid #eef1f6'` inline (líneas 620, 638 y 647), señal de que el sistema no ofrece la primitiva "separador".

El mismo patrón se repite en los paneles de métricas (`.metric-card` dentro de `.panel`), en `RunDetail` (`.run-detail-page .panel` redefine el panel base) y en `workflow-decision-card` (7 usos dentro de paneles del flujo de frotis).

### 1.2 Dos interfaces con dos trabajos distintos

| | **Workbench** (experimentación, modelos, campañas, datasets, reportes) | **Lab** (análisis de frotis inmersivo) |
|---|---|---|
| Tarea | Configurar, comparar, auditar, leer tablas | Inspeccionar imagen, decidir por célula, aprobar/rechazar caso |
| Modo de lectura | Escaneo de documento, ida y vuelta | Foco sostenido en un lienzo central |
| Fondo | Claro (`#f6f7fb`) | Oscuro (`--color-background: #0b1326`) |
| Densidad | Media; prima la legibilidad de tablas | Alta en los rieles; el lienzo manda |
| Elevación | Casi plana, basada en bordes | Paneles flotantes sobre la imagen (vidrio), es la **única** zona donde la elevación tiene función |
| Estados | De proceso (`COMPLETED`, `FAILED`, `FROZEN`) | De QC y transaccionales (aprobado, rechazado, guardando, sin conexión) |

Los dos modos son legítimos. El error actual es tratarlos como dos sistemas sin relación: dos paletas, dos escalas tipográficas y dos formas de expresar "rechazado". La propuesta es **un solo sistema con dos superficies**: mismos tokens semánticos y distintos valores según `data-surface`.

Un punto específico del Lab: el fondo actual del lienzo es azul marino (`#0b1326`). En frotis teñidos con Giemsa, un entorno con tinte azul desplaza la percepción del violeta y el rosa de los parásitos y eritrocitos (contraste simultáneo). **El área inmediata alrededor de la imagen debe ser un gris neutro** (sin tinte), aunque el cromo de la interfaz mantenga el azul de marca.

---

## 2. Tokens centralizados

### 2.1 Arquitectura en tres capas

```
primitivos      --ds-slate-100, --ds-green-700, --ds-space-4 …   (valores crudos, nunca se usan en componentes)
     ↓
semánticos      --ds-bg-canvas, --ds-border-subtle, --ds-status-approved-fg …   (varían por superficie)
     ↓
componente      --sidebar-*, --smear-*, --stage2-production-*   (alias existentes, se conservan por compatibilidad y tests)
```

Regla: **un componente solo lee tokens semánticos** (o sus alias de componente). Los primitivos existen para que los semánticos no tengan valores sueltos.

### 2.2 Archivo propuesto: `src/styles/tokens.css`

Se importa **primero** en `main.tsx`, antes de `styles.css`. Los valores de la capa semántica *Workbench* se eligieron entre los más usados hoy (`#e3e7f0`, `#62708f`, `#172033`, `#f6f7fb`, los pares de `.status-*`), para que la fase 1 no produzca cambios visuales.

```css
/* =========================================================================
   tokens.css — fuente única de verdad del sistema de diseño.
   Capa 1: primitivos. Capa 2: semánticos por superficie.
   No declarar colores, tamaños ni sombras fuera de este archivo.
   ========================================================================= */

:root {
  /* ---------- 1. PRIMITIVOS ---------- */

  /* Pizarra (neutros fríos, para el Workbench) */
  --ds-slate-0:   #ffffff;
  --ds-slate-25:  #f8faff;
  --ds-slate-50:  #f6f7fb;
  --ds-slate-100: #eef1f7;
  --ds-slate-200: #e3e7f0;
  --ds-slate-300: #cfd7e8;
  --ds-slate-400: #8a95ad;
  --ds-slate-500: #62708f;
  --ds-slate-600: #465574;
  --ds-slate-700: #27324a;
  --ds-slate-900: #172033;

  /* Noche (neutros oscuros, para el cromo del Lab; valores Material ya existentes) */
  --ds-night-0:   #060e20;
  --ds-night-50:  #0b1326;
  --ds-night-100: #131b2e;
  --ds-night-200: #171f33;
  --ds-night-300: #222a3d;
  --ds-night-400: #2d3449;
  --ds-night-500: #3c494e;
  --ds-night-600: #859399;
  --ds-night-700: #bbc9cf;
  --ds-night-800: #dae2fd;

  /* Gris neutro sin tinte: solo para el entorno inmediato de imágenes de microscopía */
  --ds-neutral-950: #121212;
  --ds-neutral-900: #1a1a1a;

  /* Marca */
  --ds-blue-600: #284a9c;
  --ds-blue-500: #315caa;
  --ds-blue-100: #eaf0ff;
  --ds-cyan-300: #a4e6ff;
  --ds-cyan-400: #4cd6ff;

  /* Estado */
  --ds-green-700: #17653b;  --ds-green-100: #e7f8ef;  --ds-green-300: #4edea3;
  --ds-amber-700: #8a5a00;  --ds-amber-100: #fff6df;  --ds-amber-300: #ffd5a5;
  --ds-red-700:   #9a2323;  --ds-red-100:   #fdecec;  --ds-red-300:   #ffb4ab;
  --ds-violet-700:#4b3a8f;  --ds-violet-100:#efecfb;  --ds-violet-300:#c9bfff;

  /* ---------- Tipografía ---------- */
  --ds-font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --ds-font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;

  --ds-text-2xs: 11px;  /* piso absoluto: chips, ejes de matriz */
  --ds-text-xs:  12px;  /* metadatos, etiquetas, celdas densas */
  --ds-text-sm:  13px;  /* cuerpo de tablas y formularios */
  --ds-text-md:  14px;  /* cuerpo general */
  --ds-text-lg:  16px;  /* título de subsección (h3) */
  --ds-text-xl:  20px;  /* título de sección (h2) */
  --ds-text-2xl: 24px;  /* título de página (h1) */

  --ds-leading-tight: 1.25;
  --ds-leading-normal: 1.5;

  --ds-weight-regular: 400;
  --ds-weight-medium: 500;
  --ds-weight-semibold: 600;
  --ds-weight-bold: 700;

  --ds-tracking-caps: .06em; /* solo para eyebrows en mayúsculas */

  /* ---------- Espaciado (base 4px) ---------- */
  --ds-space-0: 0;
  --ds-space-1: 2px;
  --ds-space-2: 4px;
  --ds-space-3: 8px;
  --ds-space-4: 12px;
  --ds-space-5: 16px;
  --ds-space-6: 24px;
  --ds-space-7: 32px;
  --ds-space-8: 48px;

  /* Ritmo vertical con nombre (lo que deben usar los layouts) */
  --ds-gap-inline: var(--ds-space-3);   /* entre controles en una fila */
  --ds-gap-field: var(--ds-space-4);    /* entre campos de un formulario */
  --ds-gap-subsection: var(--ds-space-6); /* entre subsecciones separadas por divisor */
  --ds-gap-section: var(--ds-space-6);  /* entre secciones (superficies) */
  --ds-pad-section: var(--ds-space-6);  /* padding interior de la única superficie */
  --ds-pad-control-y: var(--ds-space-3);
  --ds-pad-control-x: var(--ds-space-4);

  /* ---------- Radios ---------- */
  --ds-radius-sm: 4px;    /* chips en lienzo, celdas, checkboxes */
  --ds-radius-md: 6px;    /* inputs, botones */
  --ds-radius-lg: 8px;    /* superficies: secciones, modales, paneles flotantes */
  --ds-radius-pill: 999px;

  /* ---------- Bordes ---------- */
  --ds-border-width: 1px;
  --ds-accent-width: 3px; /* barra lateral de acento (estado/selección) */

  /* ---------- Movimiento ---------- */
  --ds-duration-fast: 120ms;
  --ds-duration-base: 180ms;
  --ds-duration-slow: 220ms;
  --ds-ease: cubic-bezier(.2, 0, 0, 1);

  /* ---------- Capas ---------- */
  --ds-z-sticky: 10;
  --ds-z-floating: 35;
  --ds-z-sidebar: 50;
  --ds-z-overlay: 100;
  --ds-z-modal: 110;

  /* ---------- Breakpoints (documentales; CSS no permite var() en @media) ---------- */
  /* sm 560px · md 720px · lg 1100px · xl 1340px */
}

/* ---------- 2. SEMÁNTICOS — superficie WORKBENCH (por defecto) ---------- */
:root,
[data-surface="workbench"] {
  color-scheme: light;

  --ds-bg-canvas: var(--ds-slate-50);       /* fondo de la página */
  --ds-bg-surface: var(--ds-slate-0);       /* la única superficie con borde */
  --ds-bg-subtle: var(--ds-slate-25);       /* filas alternas, zonas de solo-lectura */
  --ds-bg-hover: var(--ds-slate-100);
  --ds-bg-selected: var(--ds-blue-100);

  --ds-fg-default: var(--ds-slate-900);
  --ds-fg-muted: var(--ds-slate-500);
  --ds-fg-subtle: var(--ds-slate-400);
  --ds-fg-on-accent: var(--ds-slate-0);

  --ds-border-default: var(--ds-slate-200);  /* borde de superficie */
  --ds-border-subtle: var(--ds-slate-100);   /* divisores internos */
  --ds-border-strong: var(--ds-slate-300);   /* inputs */

  --ds-accent: var(--ds-blue-500);
  --ds-accent-strong: var(--ds-blue-600);
  --ds-focus-ring: 0 0 0 3px color-mix(in srgb, var(--ds-blue-500) 35%, transparent);

  /* Estados clínicos / ML. Siempre fg + bg + border + icono + texto. Nunca solo color. */
  --ds-status-approved-fg: var(--ds-green-700);
  --ds-status-approved-bg: var(--ds-green-100);
  --ds-status-approved-border: color-mix(in srgb, var(--ds-green-700) 30%, transparent);

  --ds-status-warning-fg: var(--ds-amber-700);
  --ds-status-warning-bg: var(--ds-amber-100);
  --ds-status-warning-border: color-mix(in srgb, var(--ds-amber-700) 30%, transparent);

  --ds-status-rejected-fg: var(--ds-red-700);
  --ds-status-rejected-bg: var(--ds-red-100);
  --ds-status-rejected-border: color-mix(in srgb, var(--ds-red-700) 30%, transparent);

  /* Bloqueado = restricción de gobernanza (FROZEN, campaign_guard, TEST sellado).
     No es un error: violeta + candado, para que no se confunda con "rechazado". */
  --ds-status-blocked-fg: var(--ds-violet-700);
  --ds-status-blocked-bg: var(--ds-violet-100);
  --ds-status-blocked-border: color-mix(in srgb, var(--ds-violet-700) 30%, transparent);

  --ds-status-running-fg: var(--ds-blue-600);
  --ds-status-running-bg: var(--ds-blue-100);

  --ds-status-neutral-fg: var(--ds-slate-600);
  --ds-status-neutral-bg: var(--ds-slate-100);

  /* Elevación: plana. Solo overlays reales llevan sombra. */
  --ds-elevation-0: none;
  --ds-elevation-1: 0 1px 2px rgba(18, 26, 47, .06);        /* sticky, hover de fila */
  --ds-elevation-2: 0 12px 32px rgba(18, 26, 47, .16);      /* modal, popover, drawer */
}

/* ---------- 2. SEMÁNTICOS — superficie LAB (análisis de frotis) ---------- */
[data-surface="lab"] {
  color-scheme: dark;

  --ds-bg-canvas: var(--ds-night-50);
  --ds-bg-surface: var(--ds-night-200);
  --ds-bg-subtle: var(--ds-night-100);
  --ds-bg-hover: var(--ds-night-300);
  --ds-bg-selected: var(--ds-night-400);
  --ds-bg-viewer: var(--ds-neutral-950);    /* entorno de la imagen: gris sin tinte */
  --ds-bg-glass: rgba(11, 19, 38, .74);     /* paneles flotantes sobre el lienzo */

  --ds-fg-default: var(--ds-night-800);
  --ds-fg-muted: var(--ds-night-700);
  --ds-fg-subtle: var(--ds-night-600);
  --ds-fg-on-accent: var(--ds-night-0);

  --ds-border-default: var(--ds-night-500);
  --ds-border-subtle: color-mix(in srgb, var(--ds-night-500) 55%, transparent);
  --ds-border-strong: var(--ds-night-600);
  --ds-border-glass: rgba(164, 230, 255, .17);

  --ds-accent: var(--ds-cyan-300);
  --ds-accent-strong: var(--ds-cyan-400);
  --ds-focus-ring: 0 0 0 2px var(--ds-cyan-400);

  --ds-status-approved-fg: var(--ds-green-300);
  --ds-status-approved-bg: color-mix(in srgb, var(--ds-green-300) 14%, transparent);
  --ds-status-approved-border: color-mix(in srgb, var(--ds-green-300) 40%, transparent);

  --ds-status-warning-fg: var(--ds-amber-300);
  --ds-status-warning-bg: color-mix(in srgb, var(--ds-amber-300) 14%, transparent);
  --ds-status-warning-border: color-mix(in srgb, var(--ds-amber-300) 40%, transparent);

  --ds-status-rejected-fg: var(--ds-red-300);
  --ds-status-rejected-bg: color-mix(in srgb, var(--ds-red-300) 14%, transparent);
  --ds-status-rejected-border: color-mix(in srgb, var(--ds-red-300) 40%, transparent);

  --ds-status-blocked-fg: var(--ds-violet-300);
  --ds-status-blocked-bg: color-mix(in srgb, var(--ds-violet-300) 14%, transparent);
  --ds-status-blocked-border: color-mix(in srgb, var(--ds-violet-300) 40%, transparent);

  --ds-status-running-fg: var(--ds-cyan-300);
  --ds-status-running-bg: color-mix(in srgb, var(--ds-cyan-300) 12%, transparent);

  --ds-status-neutral-fg: var(--ds-night-700);
  --ds-status-neutral-bg: var(--ds-night-300);

  --ds-elevation-0: none;
  --ds-elevation-1: 0 0 0 1px var(--ds-border-glass);
  --ds-elevation-2: 0 8px 32px rgba(0, 0, 0, .5);   /* paneles flotantes sobre la imagen */
}

/* ---------- 3. COMPATIBILIDAD: los nombres actuales pasan a ser alias ---------- */
/* Se conservan porque el CSS existente y los tests (smear-ui-refresh, model-ai-navigation…) los referencian. */
:root {
  --color-background: var(--ds-night-50);
  --color-surface-lowest: var(--ds-night-0);
  --color-surface-low: var(--ds-night-100);
  --color-surface: var(--ds-night-200);
  --color-surface-high: var(--ds-night-300);
  --color-surface-highest: var(--ds-night-400);
  --color-on-surface: var(--ds-night-800);
  --color-on-surface-variant: var(--ds-night-700);
  --color-outline: var(--ds-night-600);
  --color-outline-variant: var(--ds-night-500);
  --color-primary: var(--ds-cyan-300);
  --color-primary-container: var(--ds-cyan-400);
  --color-quality-success: var(--ds-green-300);
  --color-warning: var(--ds-amber-300);
  --color-error: var(--ds-red-300);
}

@media (prefers-contrast: more) {
  :root, [data-surface="workbench"] {
    --ds-border-default: var(--ds-slate-400);
    --ds-border-subtle: var(--ds-slate-300);
    --ds-fg-muted: var(--ds-slate-600);
  }
}
```

### 2.3 Paleta y estados: reglas de uso

| Estado | Significado en este dominio | Ejemplos en el código | Icono obligatorio |
|---|---|---|---|
| **Aprobado** | Pasa el control (QC, checks de campaña, revisión de célula aprobada, modelo en producción) | `.campaign-validation .is-pass`, `workflow-quality-status [data-state="approved"]`, `status-completed` | ✓ |
| **Advertencia** | Requiere atención y no bloquea (calidad de imagen marginal, `is-pending`) | `status-started`, `warning-panel` | ⚠ |
| **Rechazado** | Falla de dato o decisión negativa (imagen rechazada, célula rechazada, run fallido) | `status-failed`, `status-rejected`, `.is-fail` | ✗ |
| **Bloqueado** | Restricción de gobernanza: no es un error, es una regla (campaña FROZEN, TEST sellado, dataset no entrenable, `deployment-checklist [data-status="blocked"]`) | `campaign_guard`, opciones `disabled` del selector de dataset | 🔒 |
| En curso | Proceso asíncrono (entrenamiento, inferencia) | `workflow-indeterminate` | spinner/punto |
| Neutro | Sin evaluar o desconocido | `.status` base | — |

**Regla de accesibilidad:** el estado nunca se comunica solo con color. Siempre va **icono + texto + color**. Los pares `fg/bg` de Workbench ya existen en el código y cumplen contraste AA para texto de 12px en negrita. Los del Lab deben verificarse con la herramienta de contraste del navegador antes de cerrar la fase 6.

**Superposiciones sobre la imagen** (cajas de detección, Grad-CAM): no usar violeta ni magenta, que colisionan con la tinción Giemsa. Mantener cian, verde y ámbar para las cajas, y definir tokens propios (`--ds-overlay-positive`, `--ds-overlay-negative`, `--ds-overlay-uncertain`) en la fase 7.

### 2.4 Tipografía: reglas de uso

| Rol | Token | Peso | Notas |
|---|---|---|---|
| Título de página (`h1`) | `--ds-text-2xl` | 700 | Uno por página |
| Título de sección (`h2`) | `--ds-text-xl` | 600 | Abre la superficie |
| Subsección (`h3`, `legend`) | `--ds-text-lg` | 600 | Va con un divisor encima, nunca con una caja |
| Eyebrow / etiqueta en mayúsculas | `--ds-text-2xs` | 600 | `letter-spacing: var(--ds-tracking-caps)` |
| Cuerpo | `--ds-text-md` | 400 | |
| Formularios y tablas | `--ds-text-sm` | 400/500 | |
| Metadatos, `dt`, ayudas | `--ds-text-xs` | 500 | Color `--ds-fg-muted` |
| Datos numéricos | — | 500 | `font-variant-numeric: tabular-nums` (alinea columnas de métricas) |
| Identificadores (UUID, hash) | `--ds-font-mono` · `--ds-text-xs` | 400 | Truncar con `title` completo, como ya se hace |

**Reglas:** ningún texto por debajo de 11px. Solo cuatro pesos (400, 500, 600, 700). Los pesos 750, 800, 850 y 900 desaparecen. Hoy la jerarquía se fuerza con negrita extrema porque los tamaños están muy juntos; con una escala clara, 600 basta.

### 2.5 Espaciado: reglas de uso

1. **Solo valores de la escala** (2, 4, 8, 12, 16, 24, 32, 48). Los 7, 9, 10, 11, 14 y 18px se redondean al paso más cercano.
2. **El espacio comunica pertenencia** (ley de proximidad): `gap-field` (12) < `gap-subsection` (24) ≤ `gap-section` (24). Dos elementos relacionados nunca deben estar más separados que dos no relacionados.
3. **El padding vive en una sola capa:** solo la superficie tiene `--ds-pad-section`. Lo que va dentro no añade padding lateral, salvo controles.
4. **Sin márgenes inline en JSX.** Si hace falta un `marginTop`, falta una primitiva de layout.

### 2.6 Radios y elevación: reglas de uso

- **Cuatro radios:** 4 (dentro del lienzo y elementos diminutos), 6 (controles), 8 (superficies), píldora (badges). Se elimina el 18px actual del `.panel`: es lo que más "infla" la interfaz.
- **Workbench plano:** las superficies usan `border: 1px solid var(--ds-border-default)` y `box-shadow: var(--ds-elevation-0)`. La sombra `0 12px 30px` del `.panel` desaparece.
- **La sombra significa "flota sobre algo":** `elevation-2` solo para modales, popovers, el drawer móvil y los paneles flotantes del Lab sobre la imagen.
- **El vidrio (`backdrop-filter`) es exclusivo del Lab**, y solo en paneles que se superponen a la imagen (hoy hay 21 usos en el CSS del frotis y 6 en `styles.css`. De estos, 4 son del flujo de frotis y deben moverse a su hoja, y los 2 del modal de auditoría `.audit-modal-*` se justifican como overlay).

### 2.7 ¿Y Tailwind?

**No se recomienda introducir Tailwind antes de la presentación al comité.** Implicaría cambiar el build, reescribir unas 12.700 líneas de CSS o convivir con dos sistemas, y rompería los tests que leen CSS como texto.

Si más adelante se adopta, los tokens no se duplican: `tailwind.config.js` los referencia.

```js
// tailwind.config.js (futuro, opcional)
export default {
  theme: {
    colors: {
      canvas: 'var(--ds-bg-canvas)',
      surface: 'var(--ds-bg-surface)',
      fg: { DEFAULT: 'var(--ds-fg-default)', muted: 'var(--ds-fg-muted)' },
      border: { DEFAULT: 'var(--ds-border-default)', subtle: 'var(--ds-border-subtle)' },
      approved: { fg: 'var(--ds-status-approved-fg)', bg: 'var(--ds-status-approved-bg)' },
      // …
    },
    spacing: { 0: '0', 1: 'var(--ds-space-1)', 2: 'var(--ds-space-2)', /* … */ },
    borderRadius: { sm: 'var(--ds-radius-sm)', md: 'var(--ds-radius-md)', lg: 'var(--ds-radius-lg)', full: '999px' },
  },
};
```

`tokens.css` sigue siendo la fuente de verdad, y el cambio de superficie (`data-surface`) funciona igual con o sin Tailwind.

---

## 3. Layout y componentes React

### 3.1 Principio: "Capa Única de Contenedores"

> **En cualquier corte vertical de la pantalla hay como máximo UNA superficie con borde.** Todo lo que vive dentro se organiza con espacio, divisores (`border-top`) y tipografía, nunca con otra caja.

Excepciones permitidas, que no son "cajas" sino elementos con semántica propia:

- Controles de formulario (input, select, checkbox): tienen borde porque son interactivos.
- **List group:** una lista de opciones seleccionables usa un borde exterior y filas divididas por `border-top`, no un borde por opción.
- **Callout de estado:** un aviso (advertencia, bloqueado) usa fondo tintado y barra de acento izquierda de 3px. Sin borde perimetral ni sombra.
- Modales y paneles flotantes del Lab: son otra capa (elevación 2), no anidamiento.

### 3.2 Primitivas CSS (prefijo `ds-`, en `src/styles/ds-primitives.css`)

```css
.ds-page { display: grid; gap: var(--ds-gap-section); padding: var(--ds-space-6); background: var(--ds-bg-canvas); color: var(--ds-fg-default); }

/* La ÚNICA superficie. */
.ds-section {
  background: var(--ds-bg-surface);
  border: var(--ds-border-width) solid var(--ds-border-default);
  border-radius: var(--ds-radius-lg);
  box-shadow: var(--ds-elevation-0);
  padding: var(--ds-pad-section);
}
.ds-section > h2 { margin: 0 0 var(--ds-space-5); font-size: var(--ds-text-xl); font-weight: var(--ds-weight-semibold); }

/* Subsecciones: divisor + aire, sin caja. */
.ds-stack-divided > * + * {
  margin-top: var(--ds-gap-subsection);
  padding-top: var(--ds-gap-subsection);
  border-top: var(--ds-border-width) solid var(--ds-border-subtle);
}
.ds-subsection-title { margin: 0 0 var(--ds-space-4); font-size: var(--ds-text-lg); font-weight: var(--ds-weight-semibold); }

/* Lista de datos (reemplaza campaign-*-grid, cell-detail-facts, workflow-run-facts…) */
.ds-dl { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: var(--ds-space-4) var(--ds-space-5); margin: 0; }
.ds-dl dt { font-size: var(--ds-text-xs); font-weight: var(--ds-weight-medium); color: var(--ds-fg-muted); }
.ds-dl dd { margin: 0; font-size: var(--ds-text-sm); font-variant-numeric: tabular-nums; }
.ds-dl--rows { grid-template-columns: 1fr auto; } /* variante tabla clave/valor para paneles estrechos */

/* List group: un borde exterior, filas divididas */
.ds-list-group { border: var(--ds-border-width) solid var(--ds-border-default); border-radius: var(--ds-radius-md); }
.ds-list-group > * { padding: var(--ds-pad-control-y) var(--ds-pad-control-x); }
.ds-list-group > * + * { border-top: var(--ds-border-width) solid var(--ds-border-subtle); }

/* Callout de estado */
.ds-callout { padding: var(--ds-space-4) var(--ds-space-5); border-left: var(--ds-accent-width) solid currentColor; border-radius: var(--ds-radius-sm); font-size: var(--ds-text-sm); }
.ds-callout[data-tone="warning"]  { color: var(--ds-status-warning-fg);  background: var(--ds-status-warning-bg); }
.ds-callout[data-tone="blocked"]  { color: var(--ds-status-blocked-fg);  background: var(--ds-status-blocked-bg); }
.ds-callout[data-tone="rejected"] { color: var(--ds-status-rejected-fg); background: var(--ds-status-rejected-bg); }

/* Píldora de estado */
.ds-status { display: inline-flex; align-items: center; gap: var(--ds-space-2); padding: var(--ds-space-1) var(--ds-space-3); border-radius: var(--ds-radius-pill); font-size: var(--ds-text-xs); font-weight: var(--ds-weight-semibold); }
.ds-status[data-tone="approved"] { color: var(--ds-status-approved-fg); background: var(--ds-status-approved-bg); }
/* …un bloque por tono */
```

### 3.3 Componentes React (en `src/components/ui/`)

Son componentes delgados: solo aplican las clases `ds-`, sin lógica. Su función es que el JSX **no pueda** expresar una caja dentro de otra caja sin que se note en la revisión.

```tsx
// src/components/ui/Section.tsx
export function Section({ title, actions, children, divided = true }: {
  title: string; actions?: React.ReactNode; children: React.ReactNode; divided?: boolean;
}) {
  return <section className="ds-section">
    <header className="ds-section-header"><h2>{title}</h2>{actions}</header>
    <div className={divided ? 'ds-stack-divided' : undefined}>{children}</div>
  </section>;
}

// src/components/ui/Subsection.tsx — no tiene borde ni fondo: solo título + contenido
export function Subsection({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="ds-subsection"><h3 className="ds-subsection-title">{title}</h3>{children}</div>;
}

// src/components/ui/StatusPill.tsx — reemplaza StatusBadge sin romper su API
const TONE: Record<string, Tone> = {
  COMPLETED: 'approved', completed: 'approved', PASS: 'approved', approved: 'approved',
  FAILED: 'rejected', failed: 'rejected', FAIL: 'rejected', rejected: 'rejected',
  STARTED: 'running', started: 'running', RUNNING: 'running',
  FROZEN: 'blocked', blocked: 'blocked',
  warning: 'warning', PENDING: 'warning',
};
const ICON: Record<Tone, string> = { approved: '✓', warning: '⚠', rejected: '✗', blocked: '🔒', running: '●', neutral: '·' };
export function StatusPill({ status, label }: { status?: string | null; label?: string }) {
  const tone = TONE[status ?? ''] ?? 'neutral';
  return <span className="ds-status" data-tone={tone}>
    <span aria-hidden="true">{ICON[tone]}</span>{label ?? status ?? 'unknown'}
  </span>;
}
```

Catálogo mínimo: `Page`, `PageHeader`, `Section`, `Subsection`, `DescriptionList`, `ListGroup`, `Callout`, `StatusPill`, `Field` (label, control, ayuda y error) y `Toolbar`. No se recomienda Storybook ni ninguna otra dependencia en esta etapa: una página interna `/_ds` (solo en dev) que renderice cada primitiva en ambas superficies sirve como catálogo vivo y como regresión visual manual.

### 3.4 Directriz aplicada: formulario de campañas

**Antes** (5 niveles de borde) → **después** (1 nivel):

```
.ds-page
├─ PageHeader  "Configurar campaña"
├─ Callout[blocked]  "Editando «X» — campaña FROZEN, al guardar se crea una derivada"   ← reemplaza .panel.campaign-edit-banner
└─ .campaign-layout (grid 1fr / 320px)
   ├─ Section "Configuración"                       ← UNA superficie para todo el formulario
   │   (ds-stack-divided)
   │   ├─ Subsection "1. Datos generales"           → Field grid
   │   ├─ Subsection "2. Dataset version"           → Field + DescriptionList
   │   ├─ Subsection "3. Modelos y optimizadores"   → ListGroup de checks (1 borde, filas divididas)
   │   └─ Subsection "4. Configuración de modelos"
   │        ├─ por variante: título h4 + <details> como fila de disclosure (border-top, sin caja)
   │        ├─ "Métricas y EarlyStopping": legend como h4, fieldset SIN borde
   │        └─ Valores fijos: DescriptionList sobre --ds-bg-subtle (fondo, no borde) + nota de protocolo
   └─ aside (sticky)
       └─ Section "Resumen y validación"            ← fusiona 5 y 6 en una superficie
           ├─ DescriptionList--rows (total destacado con tabular-nums)
           ├─ lista de checks con StatusPill
           └─ botón primario
```

Cambios concretos:

- Se eliminan `border` y `border-radius` de `.campaign-variant`, `.campaign-model-config` y `.campaign-parameter-group`. Se reemplazan por `border-top: 1px solid var(--ds-border-subtle)` y `padding-top: var(--ds-space-5)`.
- `.campaign-check` deja de tener borde propio y pasa a ser fila de `.ds-list-group`.
- Desaparecen los tres `style={{…}}` inline.
- Se fusionan las secciones 5 y 6 del aside: el usuario ve el total y la validación como una sola unidad de decisión.
- Se mantienen la numeración de pasos y los `id`/`htmlFor` (accesibilidad y tests).

Resultado esperado: se recuperan ~100px de ancho útil, la grilla de parámetros vuelve a 3 columnas en portátil y hay 4 niveles de borde menos.

### 3.5 Directriz aplicada: análisis de frotis (Lab)

La vista ya tiene una anatomía clara. El sistema la nombra y la congela en **seis zonas**, cada una con una sola regla de contenedor:

| Zona | Componentes actuales | Contenedor | Regla |
|---|---|---|---|
| **1. Barra de caso** (arriba) | `SmearCaseHeader` | Franja a ancho completo, `border-bottom` | Sin tarjetas. ID de caso en mono, StatusPill del caso, acciones a la derecha |
| **2. Lienzo** (centro) | `CellImageViewer`, `CellGradCamPreview` | Sin cromo. Fondo `--ds-bg-viewer` (gris neutro) | Nada se dibuja encima salvo overlays de datos y la barra de control. Radio 0 |
| **3. Riel de galería** (izquierda) | `cell-gallery-panel` | Panel flotante: `--ds-bg-glass`, `--ds-border-glass`, `elevation-2`, radio 8 | Miniaturas en grilla. Estado por célula como **borde de 2px de color + icono de esquina**, no como tarjeta |
| **4. Panel de detalle / decisión** (derecha) | `cell-detail-panel`, `workflow-decision-card` | Panel flotante (misma receta) | **Dentro: cero tarjetas.** `DescriptionList--rows` para hechos, `ds-stack-divided` entre bloques (predicción → evidencia XAI → decisión → historial). `workflow-decision-card` pasa a subsección |
| **5. Barra de control** (sobre el lienzo, abajo) | `cell-controlbar-*`, `useControlBarMenu` | Píldora flotante única | Grupos separados por divisor vertical de 1px. Valores en `tabular-nums` |
| **6. Barra de estado** (pie) | `cell-review-status`, `workflow-quality-status` | Franja `border-top`, 28–32px de alto | Transaccional, con `aria-live="polite"`: *Guardando… / Guardado 14:02 / Error al guardar (reintentar) / Sin conexión*. Más contadores: revisadas X/Y, aprobadas, rechazadas |

Reglas adicionales del Lab:

- **Jerarquía por luminosidad, no por bordes:** lienzo (gris neutro) < cromo (`night-50`) < panel (`glass`) < elemento seleccionado (`night-400` + acento cian de 3px a la izquierda).
- **Densidad:** en el Lab se permite `--ds-text-xs` como cuerpo de paneles, pero nunca menos de 11px. Los 7–9px actuales del riel se reemplazan por iconos con `title`/`aria-label`.
- **Decisión clínica:** los botones Aprobar/Rechazar usan los tonos de estado en versión *sólida* (fondo `fg` del tono, texto `fg-on-accent`). Es el único lugar donde el color de estado se usa como relleno completo, para que la acción irreversible se distinga de la información.
- **Movimiento:** se conservan `smear-scan` y `prefers-reduced-motion`, ya cubiertos por tests. Todas las transiciones usan `--ds-duration-*`.
- **Se eliminan las tres declaraciones de `--smear-*`:** el contenedor raíz recibe `data-surface="lab"` y los `--smear-*` pasan a ser alias de una línea hacia `--ds-*`, declarados **una sola vez**.

---

## 4. Plan de migración

**Criterio rector:** cada fase se puede desplegar sola, no rompe `npm test` ni `npm run build`, y se puede revertir con un `git revert`. Si la presentación al comité está a menos de dos semanas, **ejecutar solo las fases 0–3**: son invisibles para el usuario o mejoran una sola página, y dejan el resto preparado.

| Fase | Qué | Riesgo visual | Archivos | Verificación |
|---|---|---|---|---|
| **0. Línea base** | Capturas de las 8 pantallas clave (Dashboard, Campañas config/reporte, Runs, RunDetail, Datasets, Deployments, Frotis en sus 3 estados) en 1440px y 390px. Registrar `npm test` y `npm run build` en verde | Ninguno | — | Carpeta `docs/audits/ui-baseline-YYYYMMDD/` |
| **1. Tokens sin cambio visual** | Crear `tokens.css` con valores **idénticos** a los actuales e importarlo primero en `main.tsx`. Redefinir `--color-*` como alias. **Conservar el texto literal** que los tests buscan | Nulo (mismos valores) | `tokens.css`, `main.tsx`, `styles.css` (`:root`) | Tests + comparación de capturas |
| **2. Barandilla automática** | Nuevo test `design-tokens.test.mjs`, en el mismo estilo de los existentes (lee CSS como texto): (a) cuenta hex/rgba fuera de `tokens.css` y falla si **sube** respecto de un umbral guardado (*ratchet*); (b) prohíbe `font-size` < 11px en código nuevo; (c) prohíbe `style={{` con `margin`/`border` en `pages/` | Nulo | `tests/design-tokens.test.mjs` | El umbral solo baja |
| **3. Primitivas + Campañas** | `ds-primitives.css` y `components/ui/*`. Migrar `CampaignConfiguration.tsx` (la vista más anidada, reciente y aislada). Mover `.campaign-field .toggle` desde `report-components.css` a su lugar | Bajo, una página | `CampaignConfiguration.tsx`, bloque `.campaign-*` de `styles.css` | `campaign-configuration.test.mjs` + revisión visual |
| **4. Estados unificados** | `StatusBadge` delega en `StatusPill` (misma API y mismas clases `status status-*` para no romper selectores). Mapear `is-pass/is-fail`, `data-state`, `data-status="blocked"` a los tonos | Bajo, cambian matices y aparecen iconos | `StatusBadge.tsx`, `.status-*` | Tests de deployments y quality-queue |
| **5. Workbench general** | Ordenadas por tráfico: Runs/RunDetail → CampaignsReport → Datasets → Deployments → Dashboard. En cada una: `.panel` anidado → `Subsection`; tipografía y espacios a la escala. Retirar la sombra y el radio de 18px del `.panel` base **al final** de la fase | Medio, acumulativo | `styles.css`, `report-components.css` (pasa a importarse en `main.tsx`) | Un PR por página, con capturas antes/después |
| **6. Lab: tokens** | `data-surface="lab"` en `.smear-workflow--immersive`. Colapsar las 3 declaraciones de `--smear-*` en una. `--ds-bg-viewer` neutro alrededor de la imagen. Verificar el contraste AA de los tonos oscuros | Bajo-medio | `smear-analysis-immersive.css` | `smear-ui-refresh`, `smear-workflow` y `smear-analysis-results-view.test.mjs` |
| **7. Lab: zonas** | Aplicar la tabla de 3.5: decisión sin tarjetas, barra de estado transaccional con `aria-live`, tokens de overlay, piso de 11px en el riel | Medio | `CellReviewWorkspace.tsx`, `SmearWorkflow.tsx`, `CellImageViewer.tsx` | Tests de cell-review + prueba manual del flujo completo con un caso real |
| **8. Limpieza** | Bajar el umbral del ratchet a cero. Borrar alias `--smear-*`/`--cell-*`/`--workflow-*` sin uso. Unificar breakpoints en los 4 documentados. Reducir los `!important` | Nulo | Todos | Ratchet = 0 |

### Por qué este orden

1. **Tokens antes que componentes:** con la fase 1 cualquier ajuste posterior se hace en un solo lugar, y no cambia nada visible, así que es seguro incluso la semana del comité.
2. **La barandilla antes de migrar:** sin el test de la fase 2, los PR de funcionalidades paralelas (`feat/menu-usuario-admin` y los que vengan) vuelven a introducir hex sueltos más rápido de lo que se migran.
3. **Campañas primero:** es el peor caso de anidamiento, tiene un solo test asociado, no comparte CSS con el Lab y el resultado es fácil de mostrar ("antes/después") al comité.
4. **El Lab al final:** concentra la mayor complejidad (2.631 líneas, 21 `backdrop-filter`, 3 modos de flujo), la mayor cantidad de tests que leen CSS y es la pantalla más importante de la demo. Se toca cuando el sistema ya está probado en el Workbench.

### Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Tests que buscan texto literal en CSS | Antes de cada fase, `grep` del selector o token en `tests/` y actualizar la aserción **en el mismo commit**, explicando por qué en el mensaje |
| `report-components.css` cargado solo vía `Runs.tsx` | En la fase 5, importarlo en `main.tsx` (o dividir: lo de campañas pasa a `ds-primitives`) |
| `color-mix()` | Soportado en Chrome/Edge 111+, Safari 16.2+ y Firefox 113+. Si el entorno de la demo es más antiguo, precalcular los valores RGBA en `tokens.css` |
| Regresión visual no detectada | Capturas de la fase 0 comparadas a mano por PR. Si se quiere automatizar después, Playwright `toHaveScreenshot` sobre las 8 pantallas |
| Divergencia con ramas en curso | Fases pequeñas (un PR por página) y mergear `main` en la rama antes de cada una |

---

## 5. Criterios de aceptación del sistema

- [ ] Un único `tokens.css` es la fuente de verdad. El ratchet de colores sueltos está en 0.
- [ ] Ninguna pantalla tiene más de una superficie con borde en un mismo corte vertical (revisable con la clase de depuración `.ds-section .ds-section { outline: 2px dashed red; }` en dev).
- [ ] ≤ 7 tamaños tipográficos, ≤ 4 pesos, ningún texto < 11px.
- [ ] ≤ 4 radios. Sombra solo en overlays.
- [ ] Los estados Aprobado/Advertencia/Rechazado/Bloqueado se ven iguales en significado en Workbench y Lab, y siempre llevan icono + texto.
- [ ] El lienzo de microscopía tiene entorno gris neutro.
- [ ] `npm test` y `npm run build` en verde en cada fase.
