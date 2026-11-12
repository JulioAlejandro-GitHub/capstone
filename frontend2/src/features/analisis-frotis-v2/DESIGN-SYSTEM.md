# CAPSTONE-FRONTEND-DS-01 — Sistema visual de Frotis v2

Implementado y auditado el **4 de noviembre de 2026**. Los valores reproducen la maqueta integrada; no se propuso una paleta nueva.

## Diagnóstico y decisión

Antes de este cambio, package.json/lockfile no incluían Tailwind ni PostCSS como dependencia directa, no existía configuración PostCSS y Vite utilizaba únicamente el plugin React. Sin embargo, `styles/module.css` ya contenía utilidades, tema y Preflight generados por **Tailwind 4.3.3**, con selectores `.af2` y propiedades internas `--af2-tw-*`. Un script requería instalar las herramientas en `/tmp` y también reescribía el HTML de referencia. Las utilidades de la maqueta ya estaban presentes en los 19 TSX del módulo.

Se instala **la misma versión 4.3.3** de `tailwindcss` y `@tailwindcss/cli`, como dependencias de desarrollo fijadas en el lockfile. Se declara directamente **PostCSS 8.5.15**, que ya era la versión transitiva del frontend. Se mantienen React **19.2.7**, Vite **7.3.5**, TypeScript **5.9.3** y las versiones de las demás dependencias existentes. No hay Tailwind v3, plugin Vite adicional ni configuración PostCSS global.

Se conserva la compilación aislada mediante CLI y transformación PostCSS. Importar Tailwind directamente desde el CSS global incorporaría Preflight a toda la aplicación; por eso el archivo de entrada `tailwind.css` **no se importa desde React**. El generador aplica `.frotis-v2` a todos los selectores antes de entregar `module.css`. Las capas se aplanan para conservar la precedencia que ya tenía la maqueta frente a las reglas sin capas del shell. `@property` y `@keyframes`, que no admiten alcance por selector, llevan nombres privados. Los atributos `className="af2 frotis-v2 ..."` mantienen `.af2` únicamente como identificador compatible con las pruebas anteriores.

La documentación oficial respalda las variables [de tema y `@theme inline`](https://tailwindcss.com/docs/theme), los efectos de [Preflight](https://tailwindcss.com/docs/preflight) y el uso de [fuentes explícitas y clases completas](https://tailwindcss.com/docs/detecting-classes-in-source-files). Se eligió `@theme inline` para que las utilidades referencien los tokens heredados en cada elemento, incluidos los descendientes de menús y modales.

## Auditoría visual

- Raíz Arial; los lugares con `font-sans` explícito conservan la pila de sistema original. Monoespaciada: ui-monospace/SFMono/Menlo/Monaco/Consolas. Esta diferencia es visible en tablas de Report y rótulos de Specimen Quality y se preserva deliberadamente.
- Marca `#4D58A4`; navegación/selección usa el índigo original de Tailwind. Son colores distintos en la maqueta y siguen siendo decisiones independientes. Los dos colores de hover de marca también se conservan.
- Superficies claras blancas/slate y galería oscura `#303338`, con sus cabeceras `#282b30` y `#23262a`. Los valores OKLCH conservan exactamente la paleta de Tailwind 4 existente.
- Espaciado base de 4 px; radios de 2/4/6/8 px; controles de perfil de 20 px; iconos comunes de 14/16 px; sidebar de 256 px y 288 px desde 640 px de viewport.
- Header con mínimo de 56 px, padding vertical de 8 px y filas que se envuelven según el espacio disponible. La altura real puede superar el mínimo. Toolbar de campo de 36 px; panel de ajustes de 300 px.
- Los 21 usos anteriores del literal de marca en TSX, incluido un comentario, pasan a cero. Se refactorizan los colores compartidos de los componentes, y se extrae el ancho inline del panel de ajustes. De las 13 expresiones `style`, permanecen 12: geometría, transformaciones, filtros y una separación que ahora referencia un token.
- Los pigmentos y gradientes específicos de células SVG, los tamaños de la superficie simulada, coordenadas, zoom, filtros de imagen y medidas derivadas permanecen en los componentes. Son representación de la demostración o geometría, no parámetros de diseño compartidos.
- No se cambian `src/styles.css`, `src/styles/tokens.css`, MUI, rutas, estado, eventos de navegación, servicios, datos clínicos ni recursos HTML independientes.

## Archivos y flujo de trabajo

| Archivo | Responsabilidad |
|---|---|
| `styles/tokens_frotis_v2.css` | Valores y alias semánticos, definidos exclusivamente en `.frotis-v2` |
| `styles/tailwind.css` | Entrada de compilación, fuentes explícitas, puente `@theme inline` y utilidad de borde |
| `styles/module.css` | Resultado generado y aislado; no editar manualmente |
| `styles/layout.css` | Integración con el shell, header, estados, capas y adaptación responsive |
| `styles/viewer.css` | Estilos de marcadores y rejilla; separados de la geometría y carga |
| `AnalisisFrotis2Page.tsx` | Importación de estilos y contenedor de alcance |
| `components/*.tsx` | Header, sidebar, galería, micrografía, visor, campo completo, calidad, reporte, ajustes, notas y tres modales usan los tokens |
| `frontend/scripts/generate-frotis-css.cjs` | Compila y aísla CSS sin escribir el HTML de referencia |
| `frontend/package.json`, `frontend/package-lock.json` | Herramientas de generación y scripts de desarrollo/build |
| `frontend/scripts/lint-frotis.mjs` | Lint opcional y limitado al módulo |
| `frontend/tests/frotis-v2-design-system.test.mjs` | Límites CSS, nombres privados, referencias y ciclos de tokens, fuentes de compilación |
| `frontend/tests/browser/frotis-v2-design.cjs` | Comparación visual, cambios de tokens en vivo y responsive |

Desde la raíz del repositorio:

```sh
npm --prefix frontend ci
npm --prefix frontend run dev
npm --prefix frontend run build
npm --prefix frontend run styles:frotis
```

`predev` y `prebuild` regeneran el CSS automáticamente. Durante una sesión de desarrollo, editar valores en `tokens_frotis_v2.css` se refleja mediante HMR, sin recompilar utilidades. **Al añadir o cambiar clases Tailwind durante esa sesión, ejecutar `styles:frotis`**; también se regeneran al reiniciar Vite o compilar. El generador no escribe si el resultado no cambió. Solo escanea los componentes, páginas y entrada del módulo; no escanea todo Capstone, los tests ni el HTML independiente.

Ejemplos de personalización desde `tokens_frotis_v2.css`:

```css
.frotis-v2 {
  --frotis-v2-primary: #4D58A4;       /* Marca, perfiles, controles y exportación */
  --frotis-v2-header-height: 56px;    /* Mínimo: permite crecimiento por contenido */
  --frotis-v2-sidebar-width: 18rem;   /* Sidebar desde el breakpoint sm */
  --frotis-v2-radius-button: 0.125rem; /* Botones/controles compactos rounded-xs */
}
```

Los botones de otros tamaños mantienen los radios `radius-sm` y `radius-md`; los chips circulares mantienen `rounded-full`. Para cambiar un tamaño de superficie, utilizar el token de su escala. El ancho compacto de sidebar es independiente del ancho de escritorio.

## Reglas de diseño

1. Usar los tokens `--frotis-v2-*` para decisiones visuales compartidas. Los componentes actuales ya consumen las utilidades semánticas `bg-frotis-*`, `text-frotis-*`, `border-frotis-*` y los tamaños `*-frotis-*`.
2. No repetir hexadecimales semánticos en TSX. Los pigmentos particulares del SVG de demostración son la excepción existente, no la paleta de controles.
3. Definir dimensiones comunes en los tokens. Mantener coordenadas, medidas de imagen, identificadores y probabilidades fuera del CSS de diseño.
4. Mantener toda regla del módulo bajo `.frotis-v2`, incluidos los estados. No añadir valores del módulo a `:root`.
5. No añadir selectores globales ni importar la entrada Tailwind sin procesar. Todo CSS servido debe pasar la prueba de aislamiento.
6. No añadir `!important`. Se conserva una sola excepción de Preflight ya existente: `.frotis-v2 [hidden]:where(:not([hidden="until-found"])) { display: none !important; }`, necesaria para que las utilidades de display no expongan elementos con atributo `hidden`. La prueba permite exclusivamente esa excepción.
7. Usar Tailwind para flex/grid, distribución, responsive, alineación, visibilidad y composición. Usar CSS específico para integración de layout y overlays complejos. No crear otro framework de componentes.
8. Usar los tokens de hover, selección, foco y deshabilitado. `focus-visible` ofrece un contorno compartido; `active` conserva una respuesta de brillo; `disabled` comparte opacidad/cursor y conserva los colores específicos. Mantener las variantes de cada superficie.
9. Conservar elementos nativos, atributos accesibles y navegación por teclado. No eliminar el contorno de foco sin reemplazarlo. Este cambio no reimplementa la accesibilidad de controles de la maqueta que ya eran divs clicables.
10. Permitir scroll **dentro del área de trabajo** donde las columnas lo requieran. No forzar anchuras que desborden el documento.
11. Mantener header con altura mínima y crecimiento por contenido. El espacio del módulo usa el viewport dinámico y el desplazamiento del shell existente; las alturas mínimas de trabajo siguen configurables, sin añadir `100vh` en componentes hijos.
12. Los modales y popovers actuales son descendientes del módulo y heredan los tokens. Si se introduce `createPortal`, montar su destino **dentro de `.frotis-v2`**. No enviar el contenido directamente a `document.body`: perdería tanto los tokens como el alcance de utilidades. Un iframe independiente tampoco hereda estos tokens.
13. Escribir clases completas y detectables. Para valores dinámicos de estado, usar opciones literales completas; para geometría, conservar estilos inline tipados. Se corrige el cursor interpolado del visor para declarar `cursor-crosshair`, `cursor-grabbing` y `cursor-grab` completos.
14. Documentar aquí cada token compartido y su propósito. Modificar el valor central, sin duplicarlo en Tailwind ni TSX.
15. Mantener las pruebas de módulos anteriores. No modificar estilos globales para resolver un problema local de Frotis v2.

## Validación y evidencia

Validación del 4 de noviembre de 2026, Node **22.23.1**, npm **10.9.8**:

| Comando / comprobación | Resultado |
|---|---|
| `npm --prefix frontend run build` | Aprobado: TypeScript de aplicación/configuración y build Vite. Se mantiene el aviso de bundle mayor a 500 kB |
| `npm --prefix frontend test` | **467/467**, sin fallos: 464 existentes y 3 pruebas de aislamiento/tokens |
| `FROTIS_LINT_PREFIX=/tmp/capstone-frotis-css npm --prefix frontend run lint:frotis` | ESLint: **24 archivos TS/TSX**, 0 errores. Reglas JS recomendadas; `no-undef` delegado a TypeScript y `no-unused-vars` desactivado para imports heredados |
| `node frontend/tests/browser/frotis-v2.cjs` con Playwright/Chrome | Aprobado: cinco rutas con recarga, menú, casos/estado, presets, layouts, detalle/reclasificación/marcado, notas, exportaciones, HTML, firma simulada, recursos y guarda de sesión |
| `node frontend/tests/browser/frotis-v2-design.cjs compare` con Playwright/Chrome/PNGJS/Pixelmatch | Aprobado: 14 comparaciones visuales y prueba de tokens en vivo |
| Responsive: cinco vistas × 390/768/1280 px | Sin scroll horizontal del documento en las 15 combinaciones |
| Cambios en vivo | Principal en perfiles y reporte; mínimo del header; ancho del sidebar; radio compacto; superficie en header/sidebar/menú/modal; activación de menú con Enter |

No existía lint global y no se afirma haber ejecutado un lint de todo Capstone. ESLint y las herramientas de navegador se instalan temporalmente para la auditoría; no se añaden dependencias de ejecución ni paquetes de lint a la aplicación.

Las capturas antes/después y resultados se encuentran en [la carpeta de evidencia](../../../../docs/engineering/frotis-v2-design-evidence/README.md). Se compara con la misma versión de Chrome, viewport de 1600×1000, animaciones desactivadas y sesión/API simuladas. Los 14 estados presentan **0 píxeles de diferencia detectada por Pixelmatch** con umbral 0.1 y exclusión de antialiasing. El JSON también registra diferencias RGBA estrictas: algunas imágenes tienen pequeñas diferencias que ese criterio excluye; no se afirma identidad binaria de todas las capturas. FULL FIELD REVIEW, SPECIMEN QUALITY, REPORT y las tres vistas externas comparadas tienen igualdad RGBA en la ejecución documentada. Se inspeccionaron capturas y diferencias durante la corrección tipográfica.

La cobertura externa incluye **Historial de análisis, Analizar imagen y Resumen de Modelo IA**, además del shell visible. No se afirma cobertura visual de todas las rutas de Capstone. No se probó una sesión real ni servicios backend. Responsive comprueba desbordamiento del documento, no certifica la usabilidad completa de cada interacción a 390 px.

Para repetir, instalar herramientas temporales con las versiones de `tool-versions.json` en la carpeta de evidencia, iniciar Vite y configurar:

```sh
FROTIS_LINT_PREFIX=/tmp/capstone-frotis-css npm --prefix frontend run lint:frotis

PLAYWRIGHT_MODULE=/tmp/capstone-frotis-css/node_modules/@playwright/test \
CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
node frontend/tests/browser/frotis-v2.cjs

PLAYWRIGHT_MODULE=/tmp/capstone-frotis-css/node_modules/@playwright/test \
PNGJS_MODULE=/tmp/capstone-frotis-css/node_modules/pngjs \
PIXELMATCH_MODULE=/tmp/capstone-frotis-css/node_modules/pixelmatch/index.js \
CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
DESIGN_EVIDENCE_DIR="$PWD/docs/engineering/frotis-v2-design-evidence" \
node frontend/tests/browser/frotis-v2-design.cjs compare
```

La ejecución documentada utilizó `FRONTEND_URL=http://127.0.0.1:5174`, porque 5173 estaba ocupado. Para generar una nueva línea base antes de un futuro cambio, ejecutar el mismo script con `capture` y un directorio distinto; no sobrescribir la evidencia histórica. Los tests capturan y comparan **páginas reales del frontend** con sesión simulada; no son renderizados de una maqueta alternativa.

## Límites y evolución del visor

No se implementan WSI, carga de imágenes reales, tiles, pirámides, segmentación, backend ni persistencia. `viewer.css` solo controla presentación de overlays; la futura lógica de carga, geometría y coordenadas debe permanecer separada. Al introducir un motor WSI, se podrán reutilizar los tokens de detección, selección, rejilla, opacidad y capas sin trasladar dimensiones de imágenes al sistema de diseño.

Los recursos HTML de referencia/descarga siguen independientes y no heredan la personalización del módulo; preservarlos evita cambiar la entrega histórica de la maqueta. Los colores SVG particulares y tamaños geométricos permanecen deliberadamente específicos. El layout conserva sus mínimos de 640/760 px, por lo que pantallas de poca altura pueden requerir scroll vertical igual que antes; no se rediseñó el shell. El informe simulado y demás limitaciones funcionales del README siguen vigentes.

## Catálogo de tokens

Los valores siguientes corresponden a `tokens_frotis_v2.css`. Los alias `var(...)` expresan relaciones deliberadas entre colores o tamaños; el valor literal existe en un solo lugar. Los prefijos `surface-inverse` y `border-inverse` corresponden a controles/paneles oscuros; las familias `selected`, `success`, `warning` y `error` conservan las variantes de superficie, borde, texto y marcador usadas por la maqueta. `text-*` define escalas tipográficas salvo los nombres explícitos de color (`text-primary`, `text-body`, etc.).

### Colores y estados

Fondos, superficies claras y oscuras, texto, bordes, estados y marca originales.

| Token | Valor original |
|---|---|
| `--frotis-v2-warning-surface` | `oklch(98.7% 0.022 95.277)` |
| `--frotis-v2-warning-subtle` | `oklch(96.2% 0.059 95.617)` |
| `--frotis-v2-warning-marker` | `oklch(82.8% 0.189 84.429)` |
| `--frotis-v2-warning-accent` | `oklch(76.9% 0.188 70.08)` |
| `--frotis-v2-warning` | `oklch(66.6% 0.179 58.318)` |
| `--frotis-v2-warning-text` | `oklch(55.5% 0.163 48.998)` |
| `--frotis-v2-success-surface` | `oklch(97.9% 0.021 166.113)` |
| `--frotis-v2-success-subtle` | `oklch(95% 0.052 163.051)` |
| `--frotis-v2-success-border` | `oklch(90.5% 0.093 164.15)` |
| `--frotis-v2-success-marker` | `oklch(76.5% 0.177 163.223)` |
| `--frotis-v2-success-accent` | `oklch(69.6% 0.17 162.48)` |
| `--frotis-v2-success` | `oklch(59.6% 0.145 163.225)` |
| `--frotis-v2-success-text` | `oklch(50.8% 0.118 165.612)` |
| `--frotis-v2-selected` | `oklch(96.2% 0.018 272.314)` |
| `--frotis-v2-selected-hover` | `oklch(93% 0.034 272.788)` |
| `--frotis-v2-selected-border` | `oklch(87% 0.065 274.039)` |
| `--frotis-v2-accent-soft` | `oklch(78.5% 0.115 274.713)` |
| `--frotis-v2-accent-muted` | `oklch(67.3% 0.182 276.935)` |
| `--frotis-v2-accent` | `oklch(58.5% 0.233 277.117)` |
| `--frotis-v2-secondary` | `oklch(51.1% 0.262 276.966)` |
| `--frotis-v2-secondary-hover` | `oklch(45.7% 0.24 277.023)` |
| `--frotis-v2-secondary-strong` | `oklch(39.8% 0.195 277.366)` |
| `--frotis-v2-secondary-dark` | `oklch(35.9% 0.144 278.697)` |
| `--frotis-v2-secondary-deep` | `oklch(25.7% 0.09 281.288)` |
| `--frotis-v2-error-subtle` | `oklch(94.1% 0.03 12.58)` |
| `--frotis-v2-error-accent` | `oklch(64.5% 0.246 16.439)` |
| `--frotis-v2-error` | `oklch(58.6% 0.253 17.585)` |
| `--frotis-v2-error-text` | `oklch(51.4% 0.222 16.935)` |
| `--frotis-v2-surface-muted` | `oklch(98.4% 0.003 247.858)` |
| `--frotis-v2-surface-subtle` | `oklch(96.8% 0.007 247.896)` |
| `--frotis-v2-border` | `oklch(92.9% 0.013 255.508)` |
| `--frotis-v2-border-strong` | `oklch(86.9% 0.022 252.894)` |
| `--frotis-v2-text-muted` | `oklch(70.4% 0.04 256.788)` |
| `--frotis-v2-text-secondary` | `oklch(55.4% 0.046 257.417)` |
| `--frotis-v2-text-control` | `oklch(44.6% 0.043 257.281)` |
| `--frotis-v2-text-body` | `oklch(37.2% 0.044 257.287)` |
| `--frotis-v2-text-heading` | `oklch(27.9% 0.041 260.031)` |
| `--frotis-v2-text-primary` | `oklch(20.8% 0.042 265.755)` |
| `--frotis-v2-overlay-base` | `#000` |
| `--frotis-v2-surface` | `#fff` |
| `--frotis-v2-background` | `#f1f5f9` |
| `--frotis-v2-surface-elevated` | `var(--frotis-v2-surface)` |
| `--frotis-v2-primary` | `#4D58A4` |
| `--frotis-v2-primary-hover` | `#3f498c` |
| `--frotis-v2-primary-reset-hover` | `#3d4787` |
| `--frotis-v2-hover` | `var(--frotis-v2-surface-subtle)` |
| `--frotis-v2-disabled` | `var(--frotis-v2-surface-muted)` |
| `--frotis-v2-gallery-surface` | `#303338` |
| `--frotis-v2-gallery-header` | `#282b30` |
| `--frotis-v2-gallery-toolbar` | `#23262a` |
| `--frotis-v2-gallery-canvas` | `#2d3035` |
| `--frotis-v2-detail-surface` | `#24272c` |
| `--frotis-v2-detail-header` | `#1e2024` |
| `--frotis-v2-surface-inverse` | `var(--frotis-v2-text-primary)` |
| `--frotis-v2-surface-inverse-raised` | `var(--frotis-v2-text-heading)` |
| `--frotis-v2-surface-inverse-elevated` | `var(--frotis-v2-text-body)` |
| `--frotis-v2-text-inverse` | `var(--frotis-v2-surface)` |
| `--frotis-v2-border-inverse` | `var(--frotis-v2-text-body)` |
| `--frotis-v2-border-inverse-strong` | `var(--frotis-v2-text-control)` |
| `--frotis-v2-border-inverse-deep` | `var(--frotis-v2-text-heading)` |

### Tipografía

Pilas tipográficas, escala de texto, pesos, alturas de línea y tracking.

| Token | Valor original |
|---|---|
| `--frotis-v2-font-family` | `Arial, sans-serif` |
| `--frotis-v2-font-sans` | `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", "Noto Sans", Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"` |
| `--frotis-v2-font-mono` | `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace` |
| `--frotis-v2-text-xs` | `0.75rem` |
| `--frotis-v2-text-xs-line-height` | `calc(1 / 0.75)` |
| `--frotis-v2-text-sm` | `0.875rem` |
| `--frotis-v2-text-sm-line-height` | `calc(1.25 / 0.875)` |
| `--frotis-v2-text-base` | `1rem` |
| `--frotis-v2-text-base-line-height` | `calc(1.5 / 1)` |
| `--frotis-v2-text-lg` | `1.125rem` |
| `--frotis-v2-text-lg-line-height` | `calc(1.75 / 1.125)` |
| `--frotis-v2-text-xl` | `1.25rem` |
| `--frotis-v2-text-xl-line-height` | `calc(1.75 / 1.25)` |
| `--frotis-v2-font-weight-normal` | `400` |
| `--frotis-v2-font-weight-medium` | `500` |
| `--frotis-v2-font-weight-semibold` | `600` |
| `--frotis-v2-font-weight-bold` | `700` |
| `--frotis-v2-tracking-tighter` | `-0.05em` |
| `--frotis-v2-tracking-tight` | `-0.025em` |
| `--frotis-v2-tracking-wide` | `0.025em` |
| `--frotis-v2-tracking-wider` | `0.05em` |
| `--frotis-v2-leading-relaxed` | `1.625` |
| `--frotis-v2-text-micro` | `8px` |
| `--frotis-v2-text-badge` | `9px` |
| `--frotis-v2-text-caption` | `10px` |
| `--frotis-v2-text-label` | `11px` |

### Espaciados

Unidad base, separación de controles/paneles y padding compartido.

| Token | Valor original |
|---|---|
| `--frotis-v2-space` | `0.25rem` |
| `--frotis-v2-header-padding-y` | `8px` |
| `--frotis-v2-control-gap` | `0.375rem` |
| `--frotis-v2-panel-gap` | `1.5rem` |
| `--frotis-v2-component-padding` | `1rem` |

### Dimensiones

Contenedores, mínimos adaptables, toolbar, sidebar, popovers, botones e iconos.

| Token | Valor original |
|---|---|
| `--frotis-v2-panel-md` | `28rem` |
| `--frotis-v2-panel-lg` | `32rem` |
| `--frotis-v2-panel-xl` | `36rem` |
| `--frotis-v2-panel-2xl` | `42rem` |
| `--frotis-v2-panel-4xl` | `56rem` |
| `--frotis-v2-header-height` | `56px` |
| `--frotis-v2-toolbar-height` | `2.25rem` |
| `--frotis-v2-sidebar-width` | `18rem` |
| `--frotis-v2-sidebar-width-compact` | `16rem` |
| `--frotis-v2-popover-width` | `300px` |
| `--frotis-v2-button-size` | `1.25rem` |
| `--frotis-v2-icon-size` | `1rem` |
| `--frotis-v2-icon-size-sm` | `0.875rem` |
| `--frotis-v2-workspace-min-height` | `640px` |
| `--frotis-v2-workspace-min-height-compact` | `760px` |
| `--frotis-v2-shell-header-height` | `64px` |

### Superficies y foco

Radios, sombras, bordes/divisores y contorno de foco.

| Token | Valor original |
|---|---|
| `--frotis-v2-radius-xs` | `var(--frotis-v2-radius-button)` |
| `--frotis-v2-radius-sm` | `0.25rem` |
| `--frotis-v2-radius-md` | `0.375rem` |
| `--frotis-v2-radius-lg` | `0.5rem` |
| `--frotis-v2-shadow-2xs` | `0 1px rgb(0 0 0 / 0.05)` |
| `--frotis-v2-shadow-xs` | `0 1px 2px 0 rgb(0 0 0 / 0.05)` |
| `--frotis-v2-shadow-sm` | `0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)` |
| `--frotis-v2-shadow-md` | `0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)` |
| `--frotis-v2-shadow-lg` | `0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)` |
| `--frotis-v2-shadow-xl` | `0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)` |
| `--frotis-v2-shadow-2xl` | `0 25px 50px -12px rgb(0 0 0 / 0.25)` |
| `--frotis-v2-shadow-inner` | `inset 0 2px 4px 0 rgb(0 0 0 / 0.05)` |
| `--frotis-v2-disabled-opacity` | `0.5` |
| `--frotis-v2-focus` | `var(--frotis-v2-accent)` |
| `--frotis-v2-focus-width` | `2px` |
| `--frotis-v2-focus-offset` | `2px` |
| `--frotis-v2-radius-button` | `0.125rem` |
| `--frotis-v2-border-width` | `1px` |
| `--frotis-v2-divider-width` | `1px` |

### Visor: presentación de overlays

Presentación del visor y overlays; excluye medidas y coordenadas de imágenes.

| Token | Valor original |
|---|---|
| `--frotis-v2-viewer-background` | `#e8d5df` |
| `--frotis-v2-viewer-slide` | `#efd7e3` |
| `--frotis-v2-viewer-minimap` | `#d8b8ca` |
| `--frotis-v2-viewer-density` | `#af5d85` |
| `--frotis-v2-micrograph-background` | `#d9b6c9` |
| `--frotis-v2-viewer-overlay` | `var(--frotis-v2-accent)` |
| `--frotis-v2-viewer-detection` | `var(--frotis-v2-accent)` |
| `--frotis-v2-viewer-selection` | `var(--frotis-v2-secondary)` |
| `--frotis-v2-viewer-hover` | `var(--frotis-v2-accent-muted)` |
| `--frotis-v2-viewer-grid` | `var(--frotis-v2-accent)` |
| `--frotis-v2-viewer-grid-opacity` | `30%` |
| `--frotis-v2-viewer-overlay-opacity` | `0.6` |
| `--frotis-v2-viewer-overlay-hover-opacity` | `1` |
| `--frotis-v2-viewer-border-width` | `1px` |
| `--frotis-v2-viewer-selected-border-width` | `2px` |
| `--frotis-v2-viewer-marker-size` | `3rem` |

### Capas

Orden de apilamiento dentro del contexto aislado del módulo.

| Token | Valor original |
|---|---|
| `--frotis-v2-z-base` | `0` |
| `--frotis-v2-z-overlay` | `10` |
| `--frotis-v2-z-toolbar` | `20` |
| `--frotis-v2-z-header` | `30` |
| `--frotis-v2-z-tooltip` | `30` |
| `--frotis-v2-z-popover` | `50` |
| `--frotis-v2-z-modal` | `50` |
