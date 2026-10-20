# CAPSTONE-UI-TOKENS.1 — Política CSS para reportes científicos

Estado documental: `CURRENT_DOC` — contrato de adopción incremental.
Fecha: 2026-10-15.
Estado técnico: implementado y validado estáticamente. **Cierre visual pendiente: sin inspección en navegador ni comparación de capturas.**

## 1. Objetivo y separación de ámbitos

Reutilizar el lenguaje visual de `/modelo-ia/ejecuciones?datasource=malaria` en futuros reportes TRAIN, EVALUATE, EXPLAIN, TEST y Comparación Científica. Esta fase no migra pantallas, modifica navegación, datos, APIs, contratos científicos ni lógica.

Análisis de frotis conserva sus componentes, CSS e interacción. `smear-analysis-immersive.css` es protegido: no se modifica ni se aplica `.ds-report` dentro de su árbol. No se alteran alias `--color-*`, superficies `lab`/`workbench` ni variables existentes. SCC-ART.1 permanece intacto. El árbol Git estaba limpio al comenzar.

## 2. Auditoría de la referencia real

`App.tsx` conecta `routes.runs` con `pages/Runs.tsx`. La página usa `.page`, `.page-title`, `.panel.report-panel`, filtros compartidos y tarjetas de linaje. No se inspeccionó el DOM en ejecución: los valores siguientes provienen del código y de su cascada declarada, no de estilos computados en navegador.

| Elemento observado | Implementación real | Convención trasladada |
|---|---|---|
| Página y encabezado | `styles.css`: `.page`, gap 22 px, padding 28 px; título 30 px | Tokens de página, `.ds-page.ds-report`, `.report-heading` |
| Superficies | Canvas #f6f7fb, panel #f8faff, tarjetas blancas | Paleta slate existente; no se crea otro tema |
| Contenedor | `.panel`: radio 18 px, sombra suave; `.report-panel`: padding 16 px | Se conserva legacy; se reutiliza densidad 16 px en secciones nuevas |
| Filtros | `ReportFilters`, `ReportSelectFilter`: 38 px, radio 8 px, gap 12 px | Altura de control, radio y espaciados compartidos |
| Filas | `RunSummaryRow`: `.report-row`, radio 14 px, sombra 0 7px 20px rgba(18,26,47,.045), celdas 15 px | Radio/sombra de tarjeta; tabla nueva semántica con padding 12 px |
| Linaje | `TrainingRunGroupCard`, `RunLineageChildCard`: TRAIN y descendientes EVALUATE/EXPLAIN; grupos radio 16 px, borde superior azul | Composición en secciones y trazabilidad; no generalizar colores de proceso como estados clínicos |
| Métricas | `MetricChip`, `MiniConfusionMatrix`, cuadrícula 2 columnas, cifras tabulares; textos 9–12 px | Reutilizar componentes existentes; nueva tarjeta grande `.report-metric` sólo cuando corresponda |
| Acciones | `.report-detail-button`, `.report-filter-clear`, `.lineage-children-toggle` | `.ds-button`: secondary por defecto, primary y warning explícitos |
| Estados | `StatusBadge`, `ReportBadge`, `RunProcessBadge`, `StatusPill` | Mantener significados separados: ejecución, evidencia, proceso; reutilizar `StatusPill` en el ámbito nuevo |
| Hover y foco | Fondos azules claros; foco rgba(49,92,170,.24); toggle usa #2d6cdf | Nuevo foco sólido con azul existente; no se retoca el foco legacy |
| Loading/error | `Loading` usa `.empty-state`; hijos usan `role=status`, `role=alert`, reintento; spinner de promoción | Texto explícito, `aria-busy`, estado semántico; no agregar animación |
| Responsive | 1340 px: encabezado oculto y filas 2 columnas; 1000 px: filtros; 700 px: filas/filtros/hijos 1 columna | Conservar breakpoints legacy; nuevos controles de 40 px y padding 10 px a 700 px |
| Identidad | `RunSummaryRow` abrevia UUID y conserva original en `title`; opciones conservan valor completo | Nuevos reportes muestran valor completo con wrap y selección; `title` solo no garantiza acceso táctil |

No se encontraron estilos `style={...}` en `Runs.tsx` ni en `components/reports/`. Sí existen en otras pantallas, por ejemplo CampaignConfiguration; fuera de alcance.

### Dependencias y conflictos

`main.tsx` importa tokens → `styles.css` → `smear-analysis-immersive.css`. `Runs.tsx` y `AssessmentDetail.tsx` importan `report-components.css`; son imports transitivos de App, por lo que no se debe inferir precedencia final sólo del orden textual de main. `ConfusionMatrix` importa su CSS propio. **`ds-primitives.css` no tiene imports en el código actual**: el consumidor futuro debe importarlo explícitamente, sin cambiar main en esta fase.

`styles.css` vuelve a declarar alias `--color-*` con literales; `.panel`, tablas, botones y títulos globales pueden competir con clases de reporte. `report-components.css` mezcla convenciones compartidas con Stage 2, campañas y linaje; contiene `!important` en matriz y badges de liberación, y tokens `--stage2-production-*` en `:root`. Se conserva todo para evitar una refactorización masiva. Mover esos tokens exige una migración posterior con revisión de cascada.

Las primitivas anteriores referencian tokens inexistentes (espaciado, tamaño, estado); algunas tienen fallback y `.ds-status` no. Definirlos ahora en `:root` cambiaría pantallas que ya consumieran esos nombres. Por eso se completan **sólo dentro de `.ds-report`**, con las mismas familias `--ds-*`: es un ámbito de adopción del sistema existente, no un tema ni un segundo sistema.

Repeticiones detectadas: blanco, #62708f, #315caa, bordes grises, radios 8 px, gaps 12/16 px y focos translúcidos. Los tonos warning/info de `ReportBadge` no coinciden exactamente con los de las primitivas: no se reemplazan por equivalencia aparente. Las nuevas primitivas usan la paleta existente. Sus textos de control son de 12 px, en vez de extender textos científicos de 9–11 px a toda la interfaz.

## 3. Responsabilidades y adopción

- `tokens.css`: sólo variables y decisiones visuales. Conserva primitivas cromáticas, superficies y alias. Nuevos tokens acotados a `.ds-report`; el único breakpoint nuevo es 700 px. CSS estándar no permite `var()` en condiciones de media queries.
- `ds-primitives.css`: presentación de página, tarjetas `.ds-section`, metadatos `.ds-dl`, badges `.ds-status`, callouts, botones, campos, navegación y acordeones. Sin paleta independiente.
- `report-components.css`: conserva íntegro el CSS anterior; añade encabezados, secciones, métricas, identificadores, tablas, evidencia, galerías, comparación y presentación de dialog. No implementa un visor XAI.

No añadir `.ds-report` a pantallas actuales sin una tarea de migración. Todos los selectores nuevos incluyen ese ámbito; no hay reglas nuevas en `:root`, body ni elementos globales. No mezclar `.ds-report` y `data-surface="lab"`. Los reportes usan `data-surface="workbench"`.

```tsx
// En el módulo del NUEVO reporte; tokens.css ya se importa desde main.
import '../styles/ds-primitives.css';
import '../styles/report-components.css';

<section className="ds-page ds-report" data-surface="workbench" aria-labelledby="report-title">
  <header className="ds-page-header">
    <h1 className="report-heading" id="report-title">Resultados científicos</h1>
  </header>
  <section className="report-section" aria-labelledby="metrics-title">
    <h2 className="ds-subsection-title" id="metrics-title">Métricas</h2>
    <MetricChip label="F1" value={f1} />
  </section>
</section>
```

Los ejemplos son fragmentos: datos y handlers pertenecen al consumidor. No se añaden componentes React, dependencias, rutas ni imports a pantallas actuales.

## 4. Inventario de tokens

### Existentes (sin modificación)

Los siguientes valores se inventarían desde `tokens.css`; se conservan sus scopes. La base slate, blue, green, amber, red y violet alimenta el contrato nuevo; night/cyan y los alias históricos quedan reservados a sus consumidores existentes. No crear sinónimos de `--ds-bg-surface`, `--ds-fg-muted` o `--ds-border-default`.

| Token | Valor existente |
|---|---|
| `--ds-slate-0` | `#ffffff` |
| `--ds-slate-25` | `#f8faff` |
| `--ds-slate-50` | `#f6f7fb` |
| `--ds-slate-100` | `#eef1f7` |
| `--ds-slate-200` | `#e3e7f0` |
| `--ds-slate-300` | `#cfd7e8` |
| `--ds-slate-400` | `#8a95ad` |
| `--ds-slate-500` | `#62708f` |
| `--ds-slate-600` | `#465574` |
| `--ds-slate-700` | `#27324a` |
| `--ds-slate-900` | `#172033` |
| `--ds-night-0` | `#060e20` |
| `--ds-night-50` | `#0b1326` |
| `--ds-night-100` | `#131b2e` |
| `--ds-night-200` | `#171f33` |
| `--ds-night-300` | `#222a3d` |
| `--ds-night-400` | `#2d3449` |
| `--ds-night-500` | `#3c494e` |
| `--ds-night-600` | `#859399` |
| `--ds-night-700` | `#bbc9cf` |
| `--ds-night-800` | `#dae2fd` |
| `--ds-neutral-950` | `#121212` |
| `--ds-blue-600` | `#284a9c` |
| `--ds-blue-500` | `#315caa` |
| `--ds-blue-100` | `#eaf0ff` |
| `--ds-cyan-300` | `#a4e6ff` |
| `--ds-cyan-400` | `#4cd6ff` |
| `--ds-green-700` | `#17653b` |
| `--ds-green-100` | `#e7f8ef` |
| `--ds-green-300` | `#4edea3` |
| `--ds-amber-700` | `#8a5a00` |
| `--ds-amber-100` | `#fff6df` |
| `--ds-amber-300` | `#ffd5a5` |
| `--ds-red-700` | `#9a2323` |
| `--ds-red-100` | `#fdecec` |
| `--ds-red-300` | `#ffb4ab` |
| `--ds-violet-700` | `#4b3a8f` |
| `--ds-violet-100` | `#efecfb` |
| `--ds-violet-300` | `#c9bfff` |
| `--ds-bg-canvas` | `var(--ds-slate-50)` |
| `--ds-bg-surface` | `var(--ds-slate-0)` |
| `--ds-bg-subtle` | `var(--ds-slate-25)` |
| `--ds-bg-hover` | `var(--ds-slate-100)` |
| `--ds-bg-selected` | `var(--ds-blue-100)` |
| `--ds-fg-default` | `var(--ds-slate-900)` |
| `--ds-fg-muted` | `var(--ds-slate-500)` |
| `--ds-border-default` | `var(--ds-slate-200)` |
| `--ds-border-subtle` | `var(--ds-slate-100)` |
| `--ds-bg-canvas` | `var(--ds-night-50)` |
| `--ds-bg-surface` | `var(--ds-night-200)` |
| `--ds-bg-subtle` | `var(--ds-night-100)` |
| `--ds-bg-viewer` | `var(--ds-neutral-950)` |
| `--ds-bg-glass` | `rgba(11, 19, 38, .74)` |
| `--ds-fg-default` | `var(--ds-night-800)` |
| `--ds-fg-muted` | `var(--ds-night-700)` |
| `--ds-border-default` | `var(--ds-night-500)` |
| `--color-background` | `var(--ds-night-50)` |
| `--color-surface-lowest` | `var(--ds-night-0)` |
| `--color-surface-low` | `var(--ds-night-100)` |
| `--color-surface` | `var(--ds-night-200)` |
| `--color-surface-high` | `var(--ds-night-300)` |
| `--color-surface-highest` | `var(--ds-night-400)` |
| `--color-on-surface` | `var(--ds-night-800)` |
| `--color-on-surface-variant` | `var(--ds-night-700)` |
| `--color-outline` | `var(--ds-night-600)` |
| `--color-outline-variant` | `var(--ds-night-500)` |
| `--color-primary` | `var(--ds-cyan-300)` |
| `--color-primary-container` | `var(--ds-cyan-400)` |
| `--color-quality-success` | `var(--ds-green-300)` |
| `--color-warning` | `var(--ds-amber-300)` |
| `--color-error` | `var(--ds-red-300)` |

Las filas repetidas corresponden a overrides de superficie: `:root/workbench` usa slate y `lab` usa night. Además siguen en `report-components.css` los cinco tokens `--stage2-production-{background,border,text,badge-background,badge-text}`, específicos de Stage 2; no se usan como tokens genéricos.

### Nuevos (scope `.ds-report`)

Espaciado y tamaños completan los nombres ya consumidos por las primitivas, respetando sus fallbacks donde los había. Radios/sombra de tarjeta y dimensiones de filtros provienen de Ejecuciones. Modal toma las convenciones del modal existente y el ancho Stage 2 de 760 px. Tamaño máximo de imagen 480 px y mínimo de galería 220 px son decisiones nuevas de presentación, pendientes de validación con artefactos reales; no cambian resolución ni transforman datos. Texto métrico 26 px procede de `.metric-card`. Estados semánticos son referencias a la paleta existente, no colores nuevos.

| Token | Valor del contrato |
|---|---|
| `--ds-space-1` | `2px` |
| `--ds-space-2` | `4px` |
| `--ds-space-3` | `8px` |
| `--ds-space-4` | `12px` |
| `--ds-space-5` | `16px` |
| `--ds-space-6` | `24px` |
| `--ds-gap-section` | `22px` |
| `--ds-gap-subsection` | `24px` |
| `--ds-pad-section` | `16px` |
| `--ds-pad-control-y` | `7px` |
| `--ds-pad-control-x` | `11px` |
| `--ds-page-padding` | `28px` |
| `--ds-border-width` | `1px` |
| `--ds-accent-width` | `3px` |
| `--ds-radius-sm` | `4px` |
| `--ds-radius-md` | `6px` |
| `--ds-radius-lg` | `8px` |
| `--ds-radius-card` | `14px` |
| `--ds-radius-modal` | `16px` |
| `--ds-radius-pill` | `999px` |
| `--ds-elevation-0` | `none` |
| `--ds-shadow-card` | `0 7px 20px rgba(18, 26, 47, .045)` |
| `--ds-shadow-modal` | `0 28px 80px rgba(0, 0, 0, .28)` |
| `--ds-font-mono` | `"SFMono-Regular", Consolas, "Liberation Mono", monospace` |
| `--ds-text-xs` | `12px` |
| `--ds-text-sm` | `13px` |
| `--ds-text-lg` | `16px` |
| `--ds-text-title` | `30px` |
| `--ds-text-metric` | `26px` |
| `--ds-line-height` | `1.45` |
| `--ds-weight-medium` | `500` |
| `--ds-weight-semibold` | `600` |
| `--ds-control-height` | `38px` |
| `--ds-control-height-compact` | `34px` |
| `--ds-focus-width` | `3px` |
| `--ds-focus-offset` | `2px` |
| `--ds-focus-color` | `var(--ds-blue-500)` |
| `--ds-action-fg` | `var(--ds-blue-500)` |
| `--ds-action-hover` | `var(--ds-blue-100)` |
| `--ds-status-approved-fg` | `var(--ds-green-700)` |
| `--ds-status-approved-bg` | `var(--ds-green-100)` |
| `--ds-status-warning-fg` | `var(--ds-amber-700)` |
| `--ds-status-warning-bg` | `var(--ds-amber-100)` |
| `--ds-status-rejected-fg` | `var(--ds-red-700)` |
| `--ds-status-rejected-bg` | `var(--ds-red-100)` |
| `--ds-status-blocked-fg` | `var(--ds-violet-700)` |
| `--ds-status-blocked-bg` | `var(--ds-violet-100)` |
| `--ds-status-running-fg` | `var(--ds-blue-600)` |
| `--ds-status-running-bg` | `var(--ds-blue-100)` |
| `--ds-status-neutral-fg` | `var(--ds-slate-600)` |
| `--ds-status-neutral-bg` | `var(--ds-slate-100)` |
| `--ds-table-cell-padding` | `12px` |
| `--ds-artifact-min-width` | `220px` |
| `--ds-artifact-max-height` | `480px` |
| `--ds-modal-width` | `760px` |
| `--ds-modal-backdrop` | `rgba(16, 24, 43, .58)` |
| `--ds-page-padding` | `10px` |
| `--ds-control-height` | `40px` |

Las últimas redefiniciones de padding y altura pertenecen a `max-width:700px`. No se han añadido aliases redundantes de colores para tablas, tarjetas o imágenes: consumen las superficies y bordes existentes.

## 5. Catálogo de elementos y variantes

Todo ejemplo nuevo vive dentro de `.ds-report[data-surface="workbench"]`. “Existente” significa que se conserva el componente y su CSS; sus valores legacy no quedan mágicamente tokenizados al usarlo. Los estados no interactivos no necesitan hover/disabled/loading artificiales.

| Elemento | React existente o recomendado | Clase CSS | Tokens principales | Variantes / estados | Ejemplo TSX |
|---|---|---|---|---|---|
| Página/contenedor | `section` nativo | `ds-page ds-report`, `ds-section` | page-padding, gap-section, bg-canvas, pad-section (prefijo `--ds-`) | workbench; responsive | `<section className="ds-page ds-report" data-surface="workbench" />` |
| Títulos/texto | h1/h2/p | `report-heading`, `ds-subsection-title`, `report-copy` | text-title, text-lg, fg-muted | principal/secundario | `<h1 className="report-heading">Reporte</h1>` |
| Botón | button nativo; no wrapper nuevo | `ds-button` | control-height, action-fg, action-hover, radius-lg | primary/secondary por defecto/warning; compact; hover/focus/disabled/busy | `<button className="ds-button" data-variant="primary" type="button" disabled={busy} aria-busy={busy}>{busy ? 'Cargando…' : 'Consultar'}</button>` |
| Badge | `StatusPill`; conservar `ReportBadge`, `StatusBadge`, `RunProcessBadge` donde ya se usan | `ds-status`; `report-badge-*` legacy | status-*-fg/bg, radius-pill | approved/warning/rejected/blocked/running/neutral; ReportBadge success/warning/info/danger/neutral | `<StatusPill status="COMPLETED" label="Completado" />` |
| Tarjeta/sección | section nativo; `TrainingRunGroupCard` específico, no duplicar | `report-section`, `ds-section` | radius-card, shadow-card, pad-section | plana (`ds-section`) / elevada; no hover implícito | `<section className="report-section" aria-label="Resultados" />` |
| Métrica | `MetricChip` existente; `dl` para valor destacado | `metric-chip` legacy, `report-metric` nuevo | text-metric, space-2; legacy sigue literal | valor / ausente (no sustituir por cero) | `<MetricChip label="F1" value={f1} />` |
| Tabla | table nativa; no usar `.report-table` legacy para tabla HTML | `report-table-scroll`, `report-data-table` | table-cell-padding, bg-subtle, border-default | hover de fila; overflow horizontal | `<div className="report-table-scroll" tabIndex={0} role="region" aria-label="Resultados"><table className="report-data-table"><caption>Métricas</caption><thead><tr><th scope="col">F1</th></tr></thead><tbody><tr><td>{f1}</td></tr></tbody></table></div>` |
| Formulario | `ReportFilters`, `ReportSelectFilter` existentes; input/select nativos nuevos | `report-filter-*` legacy; `ds-control` nuevo | control-height, border-default, status-rejected-fg | enabled/disabled/focus/invalid | `<label>Modelo<input className="ds-control" aria-invalid={invalid} aria-describedby="model-error" /></label>` |
| Acordeón | details/summary nativos; conservar toggles de linaje | `ds-accordion` | space-4, radius-lg, focus-* | abierto/cerrado/focus | `<details className="ds-accordion"><summary>Trazabilidad</summary><dl className="ds-dl">{metadata}</dl></details>` |
| Modal | dialog nativo recomendado; modales existentes son específicos de dominio | `report-viewer` | modal-width, modal-backdrop, shadow-modal, radius-modal | cerrado/showModal/escape; integración pendiente | `<dialog className="report-viewer" aria-labelledby="viewer-title"><h2 id="viewer-title">Artefacto</h2><form method="dialog"><button className="ds-button">Cerrar</button></form></dialog>` |
| Tooltip | No hay componente genérico accesible; pendiente | sólo sidebar `.is-collapsed [data-tooltip]` existente; no reutilizar fuera de sidebar | pendiente | hover/focus/Escape/táctil por implementar | `<span aria-describedby="uuid-help">UUID</span><small id="uuid-help">Identificador completo del RUN</small>` (alternativa visible) |
| Navegación | Link existente de react-router-dom; no cambiar rutas | `ds-nav-link` | control-height, action-hover, focus-* | hover/focus/aria-current | `<Link className="ds-nav-link" to={existingPath} aria-current="page">Resumen</Link>` |
| UUID/hash | code nativo; sin componente nuevo | `report-identifier` | font-mono | completo/seleccionable/wrap | `<code className="report-identifier">{runId}</code>` |
| Metadatos/trazabilidad | dl + details | `ds-dl`, `ds-dl--rows`, `ds-accordion` | text-xs/sm, space-4/5, fg-muted | resumen/detalle | `<dl className="ds-dl"><div><dt>RUN</dt><dd className="report-identifier">{runId}</dd></div></dl>` |
| Mensajes | elementos nativos; `Loading` existente no modificado | `ds-callout` | status-*-fg/bg, accent-width | approved/warning/rejected/blocked/neutral; loading con texto | `<p className="ds-callout" data-tone="rejected" role="alert">No fue posible cargar los resultados.</p>` |
| Imágenes | img/figure nativos; no reutilizar visor clínico de frotis | `report-scientific-image`, `report-artifact-gallery` | artifact-max-height/min-width, bg-subtle | disponible/ausente/error descrito en texto | `<figure><img className="report-scientific-image" src={url} alt={description} /><figcaption>{artifactName}</figcaption></figure>` |
| Evidencia | section nativo + ReportBadge existente | `report-evidence`, `report-comparison` | radius-card, shadow-card, space-4 | estados dados por contrato científico, no inferidos por CSS | `<section className="report-evidence" aria-label="Evidencia"><ReportBadge level="warning">Evidencia incompleta</ReportBadge></section>` |
| Descarga | anchor nativo, sólo URL autorizada existente | `ds-button` | action-fg, control-height, focus-* | disponible; ausente usar button disabled con explicación | `<a className="ds-button" href={downloadUrl} download>Descargar artefacto</a>` |

## 6. Convenciones UX, accesibilidad y responsive

Una página tiene un h1; secciones h2; métricas principales antes de metadatos y trazabilidad desplegable. Usar escala 2/4/8/12/16/24 px y excepciones documentadas de página; no crear variantes locales con hexadecimales. Separar contenido científico de estado operativo: color de proceso no significa éxito clínico. Toda evidencia mantiene la etiqueta textual y el dato original.

El foco nuevo es sólido, de 3 px y separado 2 px. Usar controles nativos con label, type y nombre accesible. `aria-invalid` debe acompañarse de texto asociado; `aria-busy` no bloquea interacciones por sí solo: usar disabled cuando corresponda. `aria-disabled` en enlaces tampoco impide navegación: preferir un botón deshabilitado si no hay destino. No depender del color, del hover ni del atributo title para información esencial. No añadir animaciones; las existentes requieren auditoría futura de reduced-motion.

Para nuevos reportes, medir contraste WCAG AA (4.5:1 texto normal, 3:1 texto grande y límites/foco relevantes) sobre las superficies reales antes de migrar. No se certifica aquí cumplimiento visual ni contraste de todos los estilos legacy. No trasladar textos de 9 px de matrices a formularios o párrafos.

Tablas con caption, th/scope y región de scroll enfocables cuando desbordan; no recortar columnas científicas. Galerías con minmax adaptable; imágenes con contain, sin crop ni interpolación de valores científicos. Comparaciones conservan etiquetas, escala y metadatos; CSS no valida comparabilidad. A 700 px se reduce padding y aumenta altura de controles; revisar 390/700/1000/1340/1440 px, zoom 200%, teclado y contenido largo antes de aprobar migración.

Conservar UUID y hashes completos en estado, API, DOM accesible y copia. Preferir `.report-identifier` con wrap. Si una migración necesita elipsis, debe proporcionar expansión accesible y copiar el valor original, jamás el texto abreviado. No se implementa en esta fase lógica de copia. Metadatos deben identificar RUN, versión de dataset/modelo, split y procedencia cuando estén disponibles; la ausencia se expresa como “No disponible”, sin inventar valores.

Dialog requiere apertura con showModal(), título asociado, cierre, foco inicial y retorno al disparador. Estas clases sólo proporcionan apariencia. Un portal fuera de `.ds-report` no hereda el contrato: incluir un contenedor `.ds-report[data-surface="workbench"]` para el portal, sin usarlo en frotis. Tooltip accesible y un wrapper de modal reutilizable quedan pendientes; no crear duplicados de modales de negocio.

Ejemplo CSS de extensión permitida (sólo si no existe composición equivalente):

```css
.ds-report .future-report-summary {
  display: grid;
  gap: var(--ds-space-4);
  color: var(--ds-fg-default);
}
```

## 7. Migración gradual y restricciones

1. Registrar capturas y estilos computados del reporte candidato antes de cambiarlo, con datos reproducibles y sin operaciones de escritura.
2. Importar primitivas en ese módulo y aplicar scope workbench; conservar componentes existentes que ya resuelvan filtros, badges y métricas.
3. Migrar una sección por tarea; revisar conflictos con styles.css y selectores específicos antes de sustituir valores. No introducir !important ni otro sistema de tokens.
4. Verificar vacío, carga, error, disabled, foco, contenido largo y responsive en navegador. Comparar Ejecuciones y frotis antes/después; verificar también SCC-ART.1.
5. Sólo tras validación visual ampliar al siguiente reporte. Retirar duplicaciones legacy únicamente cuando no tengan consumidores.

No Tailwind, frameworks, bibliotecas nuevas, CSS de Stitch, rutas, cambios de negocio, backend, PostgreSQL, datasets ni artefactos. No hay implementación de Grad-CAM, LIME o SHAP. No commits ni pushes. La unificación completa de paletas de badges, reducción de estilos globales, tokens Stage 2 y tooltip/modal genérico necesita tareas posteriores.

## 8. Validación y límites

- `make test-frontend`: **284/284 pruebas PASS**, sin omitidas; incluye SCC-ART, Ejecuciones y frotis. Se ejecutó el target original del Makefile dentro del contenedor frontend, suministrando el Makefile por stdin y enlazando `/app` como `frontend` en un directorio temporal. No se arrancaron servicios en el host.
- TypeScript: PASS para `tsconfig.json` y `tsconfig.node.json`, con `--noEmit --incremental false`, como parte de build.
- Vite build: PASS, 135 módulos. Advertencia no bloqueante de chunk JS mayor a 500 kB; no se cambia empaquetado.
- Sintaxis: PostCSS instalado en el contenedor parseó las tres hojas completas sin errores. Esto incluye `ds-primitives.css`, que aún no está en el bundle de la aplicación.
- Compatibilidad estática: el contenido anterior de cada una de las tres hojas es prefijo exacto del archivo final; ninguna pantalla TSX contiene `.ds-report`. No se redefinen variables globales ni se modifica CSS protegido. Esta comprobación reduce riesgo, pero no demuestra equivalencia visual.
- `git diff --check`: PASS.
- Entorno real de validación: contenedor frontend existente, Node v20.20.2, Vite v7.3.5. `package.json` declara Node >=22 <23; conviene repetir en Node 22 antes de integrar. No se alteró el contenedor ni la configuración para cambiar versiones.
- No se encontró infraestructura Playwright/Puppeteer ni snapshots visuales en frontend. No hubo herramienta de navegador disponible en esta sesión. **No hay prueba de ausencia de regresiones en navegador ni cierre visual completo.**

Archivos de esta entrega: las tres hojas CSS, este contrato y `docs/README.md` (indexación requerida). No se modifica React, `styles.css`, CSS de frotis, backend ni los archivos SCC-ART. No commits ni pushes. El contrato es reutilizable mediante adopción explícita; las pantallas actuales continúan usando sus estilos anteriores.

## Patrón: resumen + detalle tabular de verificaciones

Para colecciones homogéneas de comprobaciones científicas estructuradas:

1. **Resultado:** resumen compacto del total y estados persistidos. PASS, FAIL, ausencia de estado, advertencias y estados no clasificados deben reconciliar con el total; nunca inferir PASS por igualdad de valores.
2. **Evidencia:** tabla expandible, inicialmente cerrada, con comprobación, observado, esperado y estado. Reutilizar los datos recibidos sin consultas al abrir o cerrar. Preservar orden y distinguir cero, nulo y campo ausente.
3. **Trazabilidad:** nombre técnico original, fuentes y contenido completo accesibles mediante detalle secundario. Usar etiquetas conocidas; conservar nombres y estados desconocidos sin reinterpretarlos.

Aplicación SCC-UI-INTEGRITY.1: únicamente Integridad del dataset en A2. Una tabla compartida requiere identidad de dataset y lista ordenada de controles iguales; de otro modo se conserva el alcance por RUN. El resumen acredita los controles registrados, no todos los archivos o procesos posteriores. El patrón puede reutilizarse posteriormente para materialización, particiones, checkpoints, evaluaciones y artefactos, sin introducir una biblioteca genérica ni migrar esos módulos en esta entrega.
