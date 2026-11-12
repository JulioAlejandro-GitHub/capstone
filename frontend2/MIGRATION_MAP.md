# MIGRATION_MAP — migración `frontend/` → `frontend2/` (Tailwind CSS)

> Documento vivo de la migración. Se actualiza **después de cada componente migrado**: estado ⬜→✅, log y % de progreso.
> Fuente: `frontend/` (**solo lectura, nunca se modifica**). Destino: `frontend2/` (únicamente Tailwind CSS 4).
> Última actualización: **2026-11-10** · Fase: **1 — Inventario completado** (0 componentes migrados físicamente).

## Leyenda

| Estado | Significa |
|---|---|
| ⬜ pendiente | No migrado |
| 🔄 en progreso | En curso |
| ✅ migrado | Estilos ya resueltos con Tailwind (o infraestructura recreada) |
| ⚠️ bloqueado | No migrable de forma directa: requiere reescritura o queda fuera de alcance |
| 🚫 excepción de alcance | No se migra a Tailwind: conserva su CSS propio aislado por decisión de arquitectura |

## Excepciones de alcance (acordadas)

Estas decisiones **modifican la regla "solo Tailwind"** y son vinculantes para toda la migración:

| # | Excepción | Alcance exacto | Cómo se aplica en `frontend2/` |
|---|---|---|---|
| E1 | **material-react-table** (material-react-table.com) | `ConsensusSamplesTable.tsx`, `TrainingRunsTable.tsx`, tablas de `ScientificReport.tsx` | La librería se conserva: sus estilos los aporta MRT/MUI, no nosotros. Se eliminan de nuestros CSS los ~30 selectores `.trn-mrt .Mui*` y se migran a Tailwind **solo** contenedores, encabezados y filtros alrededor de la tabla. |
| E2 | **recharts** (recharts.github.io) | `TraceCharts.tsx`, gráficos de `ModelComparison`, `RunDetail`, `ScientificReport` | Se conserva: recharts no inyecta CSS, estiliza por props. Los selectores que hoy lo estilizan (`mx-curves polyline`, `mx-grid`, `mx-axis`, `mx-hit`, `mx-profile-series[data-tone=…]`) se trasladan a props del componente. |
| E3 | **Dominio frotis conserva su CSS** | `/frotis/analizar`, `/frotis/historial`, `/frotis/historial/:id`, `/frotis/cargar`, `/frotis/revision` (12 archivos) | Se copia un stylesheet **aislado** `src/styles/frotis-workflow.css`: reglas `.smear-workflow*` de `styles.css` + `styles/smear-analysis-immersive.css` íntegra. Dominio cerrado, no compite con Tailwind. |
| E4 | **frotis-v2 se copia tal cual** | `features/analisis-frotis-v2/**` (19 archivos + `scripts/generate-frotis-css.cjs` + CSS generado) | Maqueta de Google AI Studio, no funcional y con componentes que pueden cambiar. Se replica sin tocar lógica ni tokens. |

### Componentes cubiertos por E3 (🚫, no se traducen a Tailwind)

| Archivo | Ruta |
|---|---|
| `src/pages/SmearWorkflow.tsx` | `/frotis/analizar` |
| `src/pages/SmearAnalysisHistory.tsx` | `/frotis/historial` |
| `src/pages/SmearUpload.tsx` | `/frotis/cargar` |
| `src/components/cell-review/SmearAnalysisResultsView.tsx` | `/frotis/historial/:id` |
| `src/components/cell-review/SmearAnalysisImmersiveView.tsx` | visor inmersivo |
| `src/components/cell-review/CellReviewWorkspace.tsx` | `/frotis/revision` |
| `src/components/cell-review/CellImageViewer.tsx` | visor de células |
| `src/components/cell-review/SmearCaseHeader.tsx` | encabezado del caso |
| `src/components/cell-review/ScientificAnnotations.tsx` | anotaciones científicas |
| `src/components/cell-review/AuthenticatedCellImage.tsx` | imagen autenticada |
| `src/components/cell-review/CellGradCamPreview.tsx` | preview Grad-CAM |
| `src/components/cell-review/CellClassificationAuditModal.tsx` | auditoría de clasificación |

**Total real a convertir a Tailwind: 112 componentes** (124 − 12 🚫). Los 12 🚫 se copian sin cambios de estilo.

## 0. Foto general del origen

| Métrica | Valor |
|---|---|
| Archivos `.tsx` en `src/` | 126 |
| Componentes renderizables contabilizados | 124 |
| Archivos CSS propios | 14 (16.879 líneas, 1.705 selectores) |
| Keyframes | 12 |
| Reglas `!important` | 39 |
| `style={...}` inline | 41 ocurrencias en 14 archivos |
| Componentes con clases dinámicas | 57 |
| Librerías con estilos propios | `material-react-table`, `@mui/material` (+`x-date-pickers`, `icons-material`), `recharts` |
| Tailwind ya usado | Solo `features/analisis-frotis-v2` (Tailwind 4.3.3, CSS generado por script) |

### Reparto por tipo

| Tipo | Cantidad |
|---|---|
| primitiva | 31 |
| feature | 56 |
| layout | 7 |
| página | 30 |

### Archivos CSS que desaparecen en `frontend2`

| Archivo | Líneas | Keyframes | `@media` | `!important` | Alcance |
|---|---|---|---|---|---|
| `src/styles.css` | 8.558 | 4 | 30 | 31 | Host completo: layout, sidebar, páginas, badges, workflow de frotis legacy |
| `src/styles/smear-analysis-immersive.css` | 2.631 | 0 | 10 | 9 | Visor inmersivo de células (`cell-review`) |
| `src/styles/report-components.css` | 1.782 | 2 | 8 | 7 | Reportes, runs, ejecuciones, Stage 2, tablas MUI |
| `src/styles/scc-comparison.css` | 388 | 1 | 4 | 0 | Comparación de modelos (SCC/XAI) |
| `src/styles/model-training.css` | 279 | 0 | 4 | 1 | Escena de entrenamiento |
| `src/styles/ds-primitives.css` | 270 | 0 | 1 | 0 | Primitivas del sistema de diseño (`ds-*`) |
| `src/styles/model-explorer.css` | 216 | 4 | 3 | 1 | Explorador de modelo / arquitectura |
| `src/styles/tokens.css` | 174 | 0 | 0 | 0 | Tokens → se convierte en `@theme` |
| `src/components/ConfusionMatrix.css` | 173 | 0 | 2 | 0 | Matriz de confusión (CSS por componente) |
| `features/.../styles/tokens_frotis_v2.css` | 166 | 0 | 0 | 0 | Tokens Frotis v2 (ya `@theme inline`) |
| `features/.../styles/tailwind.css` | 139 | 0 | 0 | 0 | Fuente Tailwind del módulo |
| `features/.../styles/layout.css` | 61 | 0 | 1 | 0 | Layout del módulo |
| `features/.../styles/viewer.css` | 16 | 0 | 0 | 0 | Overlay del visor |
| `features/.../styles/module.css` | 2.026 | 1 | 9 | 1 | **Generado** por `npm run styles:frotis` (no se edita a mano) |

---

## 1. Estructura

```text
frontend/
├── index.html              # shell de Vite; carga /src/main.tsx
├── vite.config.ts          # plugin react, puerto 5173 (sin configuración de estilos)
├── tsconfig.json / tsconfig.node.json
├── package.json            # React 19, react-router 7, MUI 7, material-react-table, lucide, recharts
├── Dockerfile              # imagen del frontend (docker-compose)
├── scripts/
│   ├── generate-frotis-css.cjs   # genera module.css desde tailwind.css y lo scopea a .frotis-v2
│   └── lint-frotis.mjs           # ESLint del módulo frotis
├── public/analisis-frotis-v2/    # HTML standalone embebido en iframes (visor, scopio, aistudio)
├── tests/                        # 40 tests .test.mjs + tests/browser (Playwright, evidencia visual)
└── src/
    ├── main.tsx                  # entrada: BrowserRouter + AuthProvider + 3 CSS globales
    ├── App.tsx                   # shell: rutas, Layout, estados de ruta, selección de comparación
    ├── auth.tsx                  # AuthProvider (sin estilos propios)
    ├── router.ts                 # catálogo de rutas + helpers de URL compartible
    ├── styles.css                # 8.558 líneas de CSS global del host
    ├── styles/                   # tokens + CSS por dominio (7 archivos)
    ├── assets/                   # smear-microscope.jpg
    ├── components/               # 37 .tsx en raíz + 12 helpers .ts
    │   ├── (root)                # Layout, StatusBadge, DataTable, ConfusionMatrix, RouteState…
    │   ├── ui/                   # StatusPill (primitiva ya aislada)
    │   ├── navigation/           # AppSidebar, NavigationIcon, UserMenu, navigationConfig
    │   ├── cell-review/          # visor inmersivo de células (9 .tsx + 1 hook)
    │   ├── deployments/          # panel y modales de despliegue / Stage 2
    │   ├── explainability/       # CaseExplainabilityView + adapters
    │   ├── model-architecture/   # explorador de arquitectura (7 .tsx, 4 helpers)
    │   ├── model-training/       # escena de entrenamiento + historial (2 .tsx, 5 helpers)
    │   ├── reports/              # 38 .tsx: reportes científicos, runs, XAI, preflight
    │   └── stage2/               # Stage2EnablementModal
    ├── pages/                    # 24 páginas (/modelo-ia/* y /frotis/*)
    ├── features/analisis-frotis-v2/   # módulo ya Tailwind: 13 components + 5 pages + hooks + tokens
    ├── hooks/                    # useCellComparison, useComparisonSelection, useModelArchitecture…
    ├── services/api.ts           # cliente HTTP (no se toca)
    ├── config/pagination.ts      # constantes de paginación
    ├── data/mockData.ts          # datos de demostración
    ├── types/                    # 12 archivos de tipos
    └── utils/                    # 10 helpers de formato, lineage, atribuciones
```

### 1.1 Punto de entrada

`index.html` → `src/main.tsx` → `AuthProvider` → `App` → `Layout` + contenido por ruta.

La carga de estilos hoy es **global y por import** en `main.tsx`:

```ts
import './styles/tokens.css';
import './styles.css';
import './styles/smear-analysis-immersive.css';
```

Además, cada módulo trae su propio CSS:
- `features/analisis-frotis-v2/AnalisisFrotis2Page.tsx` → `tokens_frotis_v2.css` + `module.css` (generado).
- `components/ConfusionMatrix.tsx` → `components/ConfusionMatrix.css`.
- `report-components.css`, `model-explorer.css`, `model-training.css`, `scc-comparison.css`, `layout.css`, `viewer.css` se aplican a dominios concretos.

**En `frontend2`**: un único `styles.css` con `@import "tailwindcss";` + `@theme`, y las animaciones definidas ahí mismo. Cero archivos CSS con reglas propias.

### 1.2 Rutas de navegación

| Ruta | Página | Nota de migración |
|---|---|---|
| `/` | `Login` | shell de login sin sidebar |
| `/modelo-ia/resumen` | `Dashboard` | cards + grid |
| `/modelo-ia/ejecuciones` | `Runs` | tabla de runs (report-components) |
| `/modelo-ia/ejecuciones/:id` | `RunDetail` | 1.180 líneas / 72 clases: la página más pesada |
| `/modelo-ia/ejecuciones/:id/liberacion` | `Stage2ReleaseDetail` | panel de liberación |
| `/modelo-ia/campana` | `CampaignConfiguration` | layout grid 1fr/340px sticky |
| `/modelo-ia/campanas` | `CampaignsReport` | reporte |
| `/modelo-ia/evaluaciones` | `ClinicalEvaluation` | evaluación clínica |
| `/modelo-ia/evaluaciones/e6/:id` | `AssessmentDetail` | detalle E6 |
| `/modelo-ia/analisis` | `ModelComparison` | comparación SCC + XAI |
| `/modelo-ia/explorador` | `ModelExplorer` | arquitectura |
| `/modelo-ia/explorador/entrenamiento` | `ModelTraining` | escena + heatmap en canvas |
| `/modelo-ia/comparacion` | `CellReview` | visor legacy de células |
| `/modelo-ia/modelos-liberados` | `ModelVersions` | listado |
| `/modelo-ia/despliegues` | `Deployments` | panel de despliegue |
| `/modelo-ia/trazabilidad` | `Traceability` | |
| `/modelo-ia/explicabilidad` | `Explainability` | 481 líneas / 51 clases |
| `/modelo-ia/predicciones` | `UploadedPredictions` | upload + resultados |
| `/modelo-ia/dataset` | `DatasetBrowser` | versiones de dataset |
| `/modelo-ia/datasets-modelos` | `DatasetsModels` | |
| `/modelo-ia/errores-logs` | `ErrorsLogs` | |
| `/frotis/analisis-2` | `AnalisisFrotis2Page` | **módulo ya Tailwind** (13 components + 5 pages) |
| `/frotis/analizar` | `SmearWorkflow` | 1.264 líneas; workflow legacy con `[data-mobile-tab]` |
| `/frotis/historial` | `SmearAnalysisHistory` | |
| `/frotis/historial/:id` | `SmearAnalysisResultsView` | wrapper del visor inmersivo |
| `/frotis/cargar` | `SmearUpload` | |
| `/frotis/analisis` | `SmearAnalysisImmersiveView` | |
| `/frotis/revision` | `SmearCaseHeader` + `CellReviewWorkspace` | revisor de células |

### 1.3 Dependencias externas y su impacto visual

| Dependencia | Uso | Impacto en estilos | Decisión `frontend2` |
|---|---|---|---|
| `react` / `react-dom` / `react-router-dom` | lógica y routing | ninguno | se mantiene |
| `lucide-react` | iconos SVG | SVG inline, sin CSS | se mantiene |
| `recharts` | gráficos en 3 componentes | SVG con atributos propios; `scc-comparison.css` interviene `.recharts-scatter-symbol` | se mantiene **solo** como gráfico; todo el estilo pasa a props y al contenedor Tailwind |
| `material-react-table` | 2 tablas | inyecta sus propios estilos | **se elimina** → `DataTable` Tailwind |
| `@mui/material`, `@mui/icons-material`, `@mui/x-date-pickers` | ThemeProvider de las tablas | estilos MUI | **se elimina** |
| `tailwindcss` + `postcss` (dev) | módulo Frotis v2 | — | se promueve a dependencia base del proyecto |

---

## 2. Inventario de componentes

> Son 124 componentes: el detalle se agrupa por carpeta. **Complejidad** estimada por líneas, nº de clases, condicionales de clase y estilos inline.

### 2.1 `components/root` — 10 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/ClinicalMetricsCards.tsx` | ClinicalMetricsCards | feature | CSS global: styles.css, tokens.css | media | — | ⬜ |
| `src/components/ConfusionMatrix.tsx` | ConfusionMatrix | primitiva | CSS global: ConfusionMatrix.css, styles.css | media | — | ⬜ |
| `src/components/DataTable.tsx` | DataTable | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/DomainBadge.tsx` | DomainBadge | primitiva | CSS global: styles.css | baja | — | ✅ |
| `src/components/Layout.tsx` | Layout | layout | CSS global: styles.css, tokens.css | media | AppSidebar | ⬜ |
| `src/components/Loading.tsx` | Loading | primitiva | CSS global: styles.css | baja | — | ✅ |
| `src/components/MetricCard.tsx` | MetricCard | primitiva | utilities huérfanas (sin CSS que las defina) | baja | — | ✅ |
| `src/components/RouteState.tsx` | RouteState | primitiva | CSS global: styles.css, tokens.css | baja | — | ⬜ |
| `src/components/ScientificResults.tsx` | ScientificResults | feature | utilities huérfanas (sin CSS que las defina) | baja | — | ⬜ |
| `src/components/StatusBadge.tsx` | StatusBadge | primitiva | CSS global: styles.css | baja | — | ✅ |

### 2.2 `components/ui` — 1 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/ui/StatusPill.tsx` | StatusPill | primitiva | CSS global: styles.css | baja | — | ✅ |

### 2.3 `components/navigation` — 3 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/navigation/AppSidebar.tsx` | AppSidebar | layout | CSS global: styles.css, tokens.css | media | NavigationIcon, UserMenu | ⬜ |
| `src/components/navigation/NavigationIcon.tsx` | NavigationIcon | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/navigation/UserMenu.tsx` | UserMenu | feature | CSS global: styles.css | baja | auth | ⬜ |

### 2.4 `components/cell-review` — 9 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/cell-review/AuthenticatedCellImage.tsx` | AuthenticatedCellImage | feature | CSS global: styles.css | alta | — | 🚫 |
| `src/components/cell-review/CellClassificationAuditModal.tsx` | CellClassificationAuditModal | feature | CSS global: styles.css | baja | CaseExplainabilityView | 🚫 |
| `src/components/cell-review/CellGradCamPreview.tsx` | CellGradCamPreview | feature | CSS global: smear-analysis-immersive.css, tokens.css | media | AuthenticatedCellImage | 🚫 |
| `src/components/cell-review/CellImageViewer.tsx` | CellImageViewer | feature | CSS global: smear-analysis-immersive.css, styles.css | alta | AuthenticatedCellImage | 🚫 |
| `src/components/cell-review/CellReviewWorkspace.tsx` | CellReviewWorkspace | feature | CSS global: smear-analysis-immersive.css, styles.css | alta | AuthenticatedCellImage, CellClassificationAuditModal, CellGradCamPreview, CellImageViewer, ScientificAnnotations | 🚫 |
| `src/components/cell-review/ScientificAnnotations.tsx` | ScientificAnnotations | feature | CSS global: smear-analysis-immersive.css, styles.css | media | — | 🚫 |
| `src/components/cell-review/SmearAnalysisImmersiveView.tsx` | SmearAnalysisImmersiveView | layout | CSS global: styles.css | media | CellReviewWorkspace, ScientificAnnotations | 🚫 |
| `src/components/cell-review/SmearAnalysisResultsView.tsx` | SmearAnalysisResultsView | feature | CSS global: styles.css | baja | SmearAnalysisImmersiveView | 🚫 |
| `src/components/cell-review/SmearCaseHeader.tsx` | SmearCaseHeader | feature | CSS global: styles.css, smear-analysis-immersive.css | media | — | 🚫 |

### 2.5 `components/deployments` — 7 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/deployments/ActiveProductionModel.tsx` | ActiveProductionModel | feature | CSS global: styles.css, tokens.css | baja | StatusBadge | ⬜ |
| `src/components/deployments/ActiveStage2Model.tsx` | ActiveStage2Model | feature | CSS global: styles.css, report-components.css | baja | StatusBadge | ⬜ |
| `src/components/deployments/DeploymentReviewPanel.tsx` | DeploymentReviewPanel | feature | CSS global: styles.css, report-components.css | media | Loading, ProductionStepIndicator, StatusBadge | ⬜ |
| `src/components/deployments/ModelApprovalModal.tsx` | ModelApprovalModal | feature | CSS global: styles.css | baja | — | ✅ |
| `src/components/deployments/ProductionActivationModal.tsx` | ProductionActivationModal | feature | CSS global: styles.css | baja | — | ✅ |
| `src/components/deployments/ProductionStepIndicator.tsx` | ProductionStepIndicator | feature | utilities huérfanas (sin CSS que las defina) | baja | — | ✅ |
| `src/components/deployments/TechnicalContractModal.tsx` | TechnicalContractModal | feature | CSS global: styles.css, tokens.css | baja | — | ✅ |

### 2.6 `components/explainability` — 1 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/explainability/CaseExplainabilityView.tsx` | CaseExplainabilityView | feature | CSS global: styles.css, smear-analysis-immersive.css | alta | AuthenticatedCellImage, LegacyArtifactMedia | ⬜ |

### 2.7 `components/model-architecture` — 7 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/model-architecture/ActivationTracePanel.tsx` | ActivationTracePanel | feature | CSS global: scc-comparison.css, model-explorer.css | alta | ArchitectureChart, ComparisonPython, GeneratedXAIComparison, TraceCharts, auth, mathOperations, useComparisonSelection | ⬜ |
| `src/components/model-architecture/ArchitectureChart.tsx` | ArchitectureChart | feature | CSS global: scc-comparison.css, model-explorer.css | alta | — | ⬜ |
| `src/components/model-architecture/ArchitectureDetail.tsx` | ArchitectureDetail | feature | CSS global: styles.css | media | ActivationTracePanel, AnalysisWorkspace, ArchitectureChart, ComparisonPython, MathFunctionPanel | ⬜ |
| `src/components/model-architecture/ArchitecturePanel.tsx` | ArchitecturePanel | primitiva | CSS global: styles.css | baja | ArchitectureDetail | ⬜ |
| `src/components/model-architecture/MathFunctionPanel.tsx` | MathFunctionPanel | feature | CSS global: scc-comparison.css, report-components.css | baja | mathOperations | ⬜ |
| `src/components/model-architecture/TraceCharts.tsx` | TraceCharts | feature | CSS global: styles.css | alta | — | ⬜ |
| `src/components/model-architecture/mathOperations.tsx` | mathOperations | primitiva | CSS global: styles.css | media | — | ⬜ |

### 2.8 `components/model-training` — 2 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/model-training/TrainingHistory.tsx` | TrainingHistory | feature | CSS global: scc-comparison.css, report-components.css | alta | ScientificReport | ⚠️ |
| `src/components/model-training/TrainingScene.tsx` | TrainingScene | feature | CSS global: styles.css | alta | — | ⬜ |

### 2.9 `components/reports` — 38 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/reports/AnalysisWorkspace.tsx` | AnalysisWorkspace | feature | CSS global: scc-comparison.css, model-explorer.css | media | — | ⬜ |
| `src/components/reports/AssessmentComparison.tsx` | AssessmentComparison | feature | utilities huérfanas (sin CSS que las defina) | baja | AssessmentEvaluationCard | ⬜ |
| `src/components/reports/AssessmentEvaluationCard.tsx` | AssessmentEvaluationCard | primitiva | CSS global: styles.css | baja | MetricChip, MiniConfusionMatrix, ReportBadge, RunProcessBadge, StatusBadge | ⬜ |
| `src/components/reports/AssessmentExplanationCard.tsx` | AssessmentExplanationCard | primitiva | utilities huérfanas (sin CSS que las defina) | baja | StatusBadge | ⬜ |
| `src/components/reports/AssessmentExplanationDetail.tsx` | AssessmentExplanationDetail | primitiva | utilities huérfanas (sin CSS que las defina) | baja | ScientificArtifact, StatusBadge | ⬜ |
| `src/components/reports/AssessmentXAI.tsx` | AssessmentXAI | feature | CSS global: ds-primitives.css, tokens.css | media | GeneratedXAIComparison | ⬜ |
| `src/components/reports/AutoAnalysisBadge.tsx` | AutoAnalysisBadge | primitiva | CSS global: styles.css | baja | ReportBadge | ⬜ |
| `src/components/reports/CommandChips.tsx` | CommandChips | primitiva | CSS global: report-components.css, tokens.css | baja | — | ⬜ |
| `src/components/reports/ComparisonEligibilityStatus.tsx` | ComparisonEligibilityStatus | primitiva | CSS global: styles.css | baja | — | ✅ |
| `src/components/reports/ComparisonPython.tsx` | ComparisonPython | feature | CSS global: scc-comparison.css, ds-primitives.css | baja | NavigationIcon | ⬜ |
| `src/components/reports/ComparisonRunCard.tsx` | ComparisonRunCard | feature | CSS global: report-components.css, scc-comparison.css | baja | ComparisonPython, StatusPill | ⬜ |
| `src/components/reports/ConsensusSamplesTable.tsx` | ConsensusSamplesTable | feature | CSS global: scc-comparison.css, report-components.css | media | ComparisonPython | ⚠️ |
| `src/components/reports/DatasetIntegrity.tsx` | DatasetIntegrity | feature | CSS global: scc-comparison.css, ds-primitives.css | media | — | ⬜ |
| `src/components/reports/GeneratedXAIComparison.tsx` | GeneratedXAIComparison | feature | CSS global: styles.css | baja | XAIComparisonViewer, auth | ⬜ |
| `src/components/reports/LegacyArtifactMedia.tsx` | LegacyArtifactMedia | feature | CSS global: styles.css | baja | AuthenticatedCellImage | ⬜ |
| `src/components/reports/LineageBadge.tsx` | LineageBadge | primitiva | CSS global: styles.css | baja | ReportBadge | ⬜ |
| `src/components/reports/MetricChip.tsx` | MetricChip | primitiva | utilities huérfanas (sin CSS que las defina) | baja | — | ✅ |
| `src/components/reports/MiniConfusionMatrix.tsx` | MiniConfusionMatrix | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/reports/ReportBadge.tsx` | ReportBadge | primitiva | CSS global: styles.css | baja | — | ✅ |
| `src/components/reports/ReportFilters.tsx` | ReportFilters | primitiva | CSS global: report-components.css, tokens.css | baja | — | ✅ |
| `src/components/reports/ReportSelectFilter.tsx` | ReportSelectFilter | primitiva | CSS global: report-components.css, tokens.css | baja | — | ✅ |
| `src/components/reports/RunLineageChildCard.tsx` | RunLineageChildCard | primitiva | CSS global: styles.css | media | LineageBadge, MetricChip, MiniConfusionMatrix, ReportBadge, RunProcessBadge, StatusBadge | ⬜ |
| `src/components/reports/RunProcessBadge.tsx` | RunProcessBadge | primitiva | CSS global: styles.css | baja | — | ✅ |
| `src/components/reports/RunSelectorDialog.tsx` | RunSelectorDialog | feature | CSS global: scc-comparison.css, report-components.css | baja | TrainingRunGroupCard, TrainingRunsTable | ⬜ |
| `src/components/reports/RunSummaryRow.tsx` | RunSummaryRow | primitiva | CSS global: report-components.css, scc-comparison.css | media | AutoAnalysisBadge, CommandChips, MetricChip, MiniConfusionMatrix, NavigationIcon, RunProcessBadge, ScientificParameters, StatusBadge | ⬜ |
| `src/components/reports/ScientificArtifact.tsx` | ScientificArtifact | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/reports/ScientificParameters.tsx` | ScientificParameters | primitiva | CSS global: styles.css | baja | — | ✅ |
| `src/components/reports/ScientificPreflight.tsx` | ScientificPreflight | feature | CSS global: scc-comparison.css, report-components.css | alta | AnalysisWorkspace, ArchitecturePanel, ComparisonPython, DatasetIntegrity, ScientificReport, ScientificRepresentations, auth | ⬜ |
| `src/components/reports/ScientificReport.tsx` | ScientificReport | feature | CSS global: scc-comparison.css, report-components.css | alta | AnalysisWorkspace, AssessmentXAI, ComparisonPython, ConsensusSamplesTable, GeneratedXAIComparison | ⬜ |
| `src/components/reports/ScientificRepresentations.tsx` | ScientificRepresentations | feature | CSS global: scc-comparison.css, report-components.css | media | AnalysisWorkspace, ComparisonPython, ScientificReport | ⬜ |
| `src/components/reports/Stage2PublicationPanel.tsx` | Stage2PublicationPanel | feature | CSS global: report-components.css, tokens.css | media | — | ⬜ |
| `src/components/reports/TrainingExplanationAttempt.tsx` | TrainingExplanationAttempt | feature | utilities huérfanas (sin CSS que las defina) | baja | AssessmentExplanationDetail, StatusBadge | ⬜ |
| `src/components/reports/TrainingRunGroupCard.tsx` | TrainingRunGroupCard | feature | CSS global: report-components.css, tokens.css | media | AssessmentEvaluationCard, AssessmentExplanationCard, RunLineageChildCard, RunSummaryRow, Stage2PublicationPanel | ⬜ |
| `src/components/reports/TrainingRunsTable.tsx` | TrainingRunsTable | feature | CSS global: report-components.css, scc-comparison.css | alta | RunSummaryRow | ⚠️ |
| `src/components/reports/TrainingXAIComparison.tsx` | TrainingXAIComparison | feature | CSS global: ds-primitives.css, report-components.css | media | GeneratedXAIComparison | ⬜ |
| `src/components/reports/UnlinkedRunsSection.tsx` | UnlinkedRunsSection | feature | CSS global: report-components.css, tokens.css | media | ReportBadge, RunProcessBadge, StatusBadge | ⬜ |
| `src/components/reports/XAIComparisonViewer.tsx` | XAIComparisonViewer | feature | CSS global: scc-comparison.css, report-components.css | media | XAIOverlayView | ⬜ |
| `src/components/reports/XAIOverlayView.tsx` | XAIOverlayView | feature | CSS global: scc-comparison.css, model-explorer.css | media | XAIComparisonViewer | ⬜ |

### 2.10 `components/stage2` — 1 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/stage2/Stage2EnablementModal.tsx` | Stage2EnablementModal | feature | CSS global: report-components.css, tokens.css | baja | — | ⬜ |

### 2.11 `pages` — 24 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/pages/AssessmentDetail.tsx` | AssessmentDetail | página | utilities huérfanas (sin CSS que las defina) | baja | AssessmentEvaluationCard, AssessmentExplanationDetail, AssessmentXAI, Loading, RouteState | ⬜ |
| `src/pages/CampaignConfiguration.tsx` | CampaignConfiguration | página | CSS global: styles.css, report-components.css | alta | Loading | ⬜ |
| `src/pages/CampaignsReport.tsx` | CampaignsReport | página | CSS global: styles.css, tokens.css | media | Loading | ⬜ |
| `src/pages/CellReview.tsx` | CellReview | página | CSS global: styles.css, tokens.css | alta | CellReviewWorkspace, auth | ⬜ |
| `src/pages/ClinicalEvaluation.tsx` | ClinicalEvaluation | página | CSS global: styles.css, tokens.css | media | DataTable, Loading | ⬜ |
| `src/pages/Dashboard.tsx` | Dashboard | página | CSS global: styles.css, tokens.css | media | DataTable, DomainBadge, Loading, MetricCard, StatusBadge | ⬜ |
| `src/pages/DatasetBrowser.tsx` | DatasetBrowser | página | CSS global: styles.css, tokens.css | media | Loading | ⬜ |
| `src/pages/DatasetsModels.tsx` | DatasetsModels | página | CSS global: styles.css | media | DataTable, DomainBadge, Loading | ⬜ |
| `src/pages/Deployments.tsx` | Deployments | página | CSS global: styles.css | media | ActiveProductionModel, ActiveStage2Model, DataTable, DeploymentReviewPanel, Loading, ModelApprovalModal, ProductionActivationModal, RouteState, Stage2EnablementModal, StatusBadge, TechnicalContractModal | ⬜ |
| `src/pages/ErrorsLogs.tsx` | ErrorsLogs | página | CSS global: styles.css | media | DataTable, Loading | ⬜ |
| `src/pages/Explainability.tsx` | Explainability | página | CSS global: styles.css, tokens.css | alta | CaseExplainabilityView, DataTable, Loading, auth | ⬜ |
| `src/pages/Login.tsx` | Login | página | CSS global: styles.css, tokens.css | media | auth | ⬜ |
| `src/pages/ModelComparison.tsx` | ModelComparison | página | CSS global: scc-comparison.css, report-components.css | media | AnalysisWorkspace, ComparisonEligibilityStatus, ComparisonRunCard, RunSelectorDialog, ScientificPreflight, ScientificReport, auth, useComparisonSelection | ⬜ |
| `src/pages/ModelExplorer.tsx` | ModelExplorer | página | CSS global: report-components.css, scc-comparison.css | baja | AnalysisWorkspace, ArchitectureDetail, RunSelectorDialog | ⬜ |
| `src/pages/ModelTraining.tsx` | ModelTraining | página | CSS global: styles.css | alta | GeneratedXAIComparison, TrainingHistory, TrainingScene, XAIComparisonViewer | ⬜ |
| `src/pages/ModelVersions.tsx` | ModelVersions | página | CSS global: styles.css, tokens.css | media | DataTable, Loading, RouteState, StatusBadge | ⬜ |
| `src/pages/RunDetail.tsx` | RunDetail | página | CSS global: styles.css, report-components.css | alta | AssessmentXAI, ClinicalMetricsCards, ConfusionMatrix, DataTable, Explainability, LegacyArtifactMedia, Loading, RouteState, ScientificArtifact, ScientificResults, StatusBadge, TrainingExplanationAttempt, TrainingXAIComparison | ⬜ |
| `src/pages/Runs.tsx` | Runs | página | CSS global: report-components.css, styles.css | alta | Loading, RunSummaryRow, TrainingRunGroupCard, TrainingRunsTable | ⬜ |
| `src/pages/SmearAnalysisHistory.tsx` | SmearAnalysisHistory | página | CSS global: styles.css, tokens.css | media | SmearWorkflow | 🚫 |
| `src/pages/SmearUpload.tsx` | SmearUpload | página | CSS global: styles.css, tokens.css | alta | — | 🚫 |
| `src/pages/SmearWorkflow.tsx` | SmearWorkflow | página | CSS global: styles.css, smear-analysis-immersive.css | alta | SmearAnalysisImmersiveView, SmearCaseHeader, SmearUpload, auth | 🚫 |
| `src/pages/Stage2ReleaseDetail.tsx` | Stage2ReleaseDetail | página | CSS global: styles.css, tokens.css | media | Loading, RouteState, Stage2EnablementModal | ⬜ |
| `src/pages/Traceability.tsx` | Traceability | página | CSS global: styles.css | baja | Loading | ⬜ |
| `src/pages/UploadedPredictions.tsx` | UploadedPredictions | página | CSS global: styles.css, tokens.css | alta | DataTable, LegacyArtifactMedia, Loading, StatusBadge | ⬜ |

### 2.12 `features/analisis-frotis-v2` — 19 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/features/analisis-frotis-v2/AnalisisFrotis2Page.tsx` | AnalisisFrotis2Page | página | Tailwind utilities + @theme (frotis-v2) | media | AnalysisAreaPage, CellDetailModal, ExportModal, FullFieldReviewPage, Header, NotesDrawer, ReportPage, ReviewCellsPage, SpecimenQualityPage, StandaloneHtmlModal | ✅ |
| `src/features/analisis-frotis-v2/components/CellDetailModal.tsx` | CellDetailModal | primitiva | Tailwind utilities + @theme (frotis-v2) | alta | CellMicrograph | ✅ |
| `src/features/analisis-frotis-v2/components/CellGallery.tsx` | CellGallery | feature | Tailwind utilities + @theme (frotis-v2) | alta | CellMicrograph | ✅ |
| `src/features/analisis-frotis-v2/components/CellMicrograph.tsx` | CellMicrograph | primitiva | Tailwind utilities + @theme (frotis-v2) | alta | — | ✅ |
| `src/features/analisis-frotis-v2/components/DifferentialSidebar.tsx` | DifferentialSidebar | feature | Tailwind utilities + @theme (frotis-v2) | alta | — | ✅ |
| `src/features/analisis-frotis-v2/components/ExportModal.tsx` | ExportModal | feature | Tailwind utilities + @theme (frotis-v2) | alta | — | ✅ |
| `src/features/analisis-frotis-v2/components/FullFieldView.tsx` | FullFieldView | feature | Tailwind utilities + @theme (frotis-v2) | alta | SlideViewer | ✅ |
| `src/features/analisis-frotis-v2/components/Header.tsx` | Header | layout | Tailwind utilities + @theme (frotis-v2) | alta | ImageAdjustmentsPopover | ✅ |
| `src/features/analisis-frotis-v2/components/ImageAdjustmentsPopover.tsx` | ImageAdjustmentsPopover | primitiva | Tailwind utilities + @theme (frotis-v2) | alta | — | ✅ |
| `src/features/analisis-frotis-v2/components/NotesDrawer.tsx` | NotesDrawer | feature | Tailwind utilities + @theme (frotis-v2) | alta | — | ✅ |
| `src/features/analisis-frotis-v2/components/QualityView.tsx` | QualityView | feature | Tailwind utilities + @theme (frotis-v2) | alta | — | ✅ |
| `src/features/analisis-frotis-v2/components/ReportView.tsx` | ReportView | feature | Tailwind utilities + @theme (frotis-v2) | alta | — | ✅ |
| `src/features/analisis-frotis-v2/components/SlideViewer.tsx` | SlideViewer | layout | Tailwind utilities + @theme (frotis-v2) | alta | ImageAdjustmentsPopover | ✅ |
| `src/features/analisis-frotis-v2/components/StandaloneHtmlModal.tsx` | StandaloneHtmlModal | feature | Tailwind utilities + @theme (frotis-v2) | alta | — | ✅ |
| `src/features/analisis-frotis-v2/pages/AnalysisAreaPage.tsx` | AnalysisAreaPage | página | Tailwind utilities + @theme (frotis-v2) | baja | FullFieldView | ✅ |
| `src/features/analisis-frotis-v2/pages/FullFieldReviewPage.tsx` | FullFieldReviewPage | página | Tailwind utilities + @theme (frotis-v2) | baja | FullFieldView | ✅ |
| `src/features/analisis-frotis-v2/pages/ReportPage.tsx` | ReportPage | página | Tailwind utilities + @theme (frotis-v2) | baja | ReportView | ✅ |
| `src/features/analisis-frotis-v2/pages/ReviewCellsPage.tsx` | ReviewCellsPage | página | Tailwind utilities + @theme (frotis-v2) | baja | CellGallery, DifferentialSidebar, SlideViewer | ✅ |
| `src/features/analisis-frotis-v2/pages/SpecimenQualityPage.tsx` | SpecimenQualityPage | página | Tailwind utilities + @theme (frotis-v2) | baja | QualityView | ✅ |

### 2.13 `(root)` — 4 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/App.tsx` | App | layout | CSS global: styles.css | media | AnalisisFrotis2Page, AssessmentDetail, CampaignConfiguration, CampaignsReport, ClinicalEvaluation, Dashboard, DatasetBrowser, DatasetsModels, Deployments, ErrorsLogs, Explainability, Layout, Login, ModelComparison, ModelExplorer, ModelTraining, ModelVersions, RouteState, RunDetail, Runs, SmearAnalysisHistory, SmearWorkflow, Stage2ReleaseDetail, Traceability, UploadedPredictions, auth, useComparisonSelection | ⬜ |
| `src/auth.tsx` | auth | layout | CSS global: styles.css | media | — | ⬜ |
| `src/hooks/useComparisonSelection.tsx` | useComparisonSelection | hook | CSS global: styles.css | baja | — | — |
| `src/main.tsx` | main | entrada | CSS global: styles.css | baja | App, auth | — |

### 2.14 Lógica sin capa visual (se copia sin cambios de estilos)

`hooks/` (6), `utils/` (10), `types/` (12), `services/api.ts`, `config/pagination.ts`, `data/mockData.ts`, `router.ts`, `auth.tsx`, `navigationConfig.ts`, `architectureViews.ts`, `traceCode.ts`, `traceColor.ts`, `traceSteps.ts`, `cellModel.ts`, `trainingModel.ts`, `trainingHistoryModel.ts`, `explainabilityCaseAdapters.ts`, `useControlBarMenu.ts`, `xai/comparison.ts`, `runDetail.ts`, `runReport.ts`, `lineageSlots.ts`, `preflightPresentation.ts`, `datasetChecks.ts`, `comparisonCache.ts`, `attributionMaps.ts`, `analysisSummaries.ts`, `format.ts`, `explainability.ts`, `mathOperations.tsx` (genera SVG sin CSS).

---

## 5. Orden de migración (de hoja a raíz)

El orden se derivó del grafo de dependencias internas: un componente se migra **después** de todos los que importa. Onda 0 es infraestructura y Onda 6 es el dominio frotis, que por la excepción E3 no se convierte a Tailwind.

### Onda 0 — Infraestructura (antes de cualquier componente) — 0 componente(s)

- [x] `frontend2/package.json` — React 19, react-router 7, lucide-react, recharts, material-react-table (E1), `tailwindcss` 4.3.3.
- [x] `frontend2/vite.config.ts`, `tsconfig.json`, `tsconfig.node.json`, `index.html`, `Dockerfile`, `postcss.config.cjs`.
- [x] `frontend2/src/styles.css` — `@import "tailwindcss"` + `@theme`: única hoja de estilos del sistema general.
- [x] Copia de `src/types/`, `src/utils/`, `src/services/`, `src/config/`, `src/hooks/`, `src/assets/`, `src/router.ts`, `src/components/**` (54 helpers `.ts`), `public/`, `tests/`.
- [ ] `frontend2/src/main.tsx` y `frontend2/src/App.tsx` — se crean con la Onda 3.
- [x] `frontend2/src/styles/frotis-workflow.css` — creado: 474 reglas del dominio frotis + 66 reglas genéricas re-escoped a las raíces `.smear-workflow`, `.cell-*`, `.frotis-*`, etc. (E3).
- [ ] `frontend2/.env.example` — `VITE_API_BASE_URL`, `VITE_DEFAULT_DATASOURCE`.

### Onda 1 — Primitivas (sin dependencias internas) — 35 componente(s)

- [ ] `src/auth.tsx` → `frontend2/src/auth.tsx`
- [ ] `src/components/ClinicalMetricsCards.tsx` → `frontend2/src/components/ClinicalMetricsCards.tsx`
- [ ] `src/components/ConfusionMatrix.tsx` → `frontend2/src/components/ConfusionMatrix.tsx` — Tiene CSS propio (`ConfusionMatrix.css`, 173 líneas) y modificadores `--${result}${priority}`. Reproducir las 4 combinaciones como mapa de clases; el resto del layout con utilities.
- [ ] `src/components/DataTable.tsx` → `frontend2/src/components/DataTable.tsx` — Base para reemplazar material-react-table: implementar paginación, sort y filtros como props, sin librería.
- [x] `src/components/DomainBadge.tsx` → `frontend2/src/components/DomainBadge.tsx`
- [x] `src/components/Loading.tsx` → `frontend2/src/components/Loading.tsx`
- [x] `src/components/MetricCard.tsx` → `frontend2/src/components/MetricCard.tsx` — Usa utilities huérfanas (`flex`, `text-xs`) que hoy no defina ningún CSS: se convierten en utilities reales de Tailwind, sin pérdida de comportamiento.
- [ ] `src/components/RouteState.tsx` → `frontend2/src/components/RouteState.tsx`
- [ ] `src/components/ScientificResults.tsx` → `frontend2/src/components/ScientificResults.tsx`
- [x] `src/components/StatusBadge.tsx` → `frontend2/src/components/StatusBadge.tsx` — Clases `status` + `status-${normalized}` definidas en `styles.css`. Mapeo: objeto `STATUS_TONE = {ok:[...], warning:[...], error:[...]}` que devuelve utilities literales (Tailwind no permite nombres de clase dinámicos).
- [x] `src/components/deployments/ModelApprovalModal.tsx` → `frontend2/src/components/deployments/ModelApprovalModal.tsx`
- [x] `src/components/deployments/ProductionActivationModal.tsx` → `frontend2/src/components/deployments/ProductionActivationModal.tsx`
- [x] `src/components/deployments/ProductionStepIndicator.tsx` → `frontend2/src/components/deployments/ProductionStepIndicator.tsx`
- [x] `src/components/deployments/TechnicalContractModal.tsx` → `frontend2/src/components/deployments/TechnicalContractModal.tsx`
- [ ] `src/components/model-architecture/ArchitectureChart.tsx` → `frontend2/src/components/model-architecture/ArchitectureChart.tsx`
- [ ] `src/components/model-architecture/TraceCharts.tsx` → `frontend2/src/components/model-architecture/TraceCharts.tsx`
- [ ] `src/components/model-architecture/mathOperations.tsx` → `frontend2/src/components/model-architecture/mathOperations.tsx`
- [ ] `src/components/model-training/TrainingScene.tsx` → `frontend2/src/components/model-training/TrainingScene.tsx` — Clases `mt-root` y `mt-halo` no están definidas en ningún CSS (estilo inerte). Reconstruir con utilities + keyframes del theme.
- [ ] `src/components/navigation/NavigationIcon.tsx` → `frontend2/src/components/navigation/NavigationIcon.tsx`
- [ ] `src/components/reports/AnalysisWorkspace.tsx` → `frontend2/src/components/reports/AnalysisWorkspace.tsx`
- [ ] `src/components/reports/CommandChips.tsx` → `frontend2/src/components/reports/CommandChips.tsx`
- [x] `src/components/reports/ComparisonEligibilityStatus.tsx` → `frontend2/src/components/reports/ComparisonEligibilityStatus.tsx`
- [ ] `src/components/reports/DatasetIntegrity.tsx` → `frontend2/src/components/reports/DatasetIntegrity.tsx`
- [x] `src/components/reports/MetricChip.tsx` → `frontend2/src/components/reports/MetricChip.tsx`
- [ ] `src/components/reports/MiniConfusionMatrix.tsx` → `frontend2/src/components/reports/MiniConfusionMatrix.tsx` — Primitiva de reporte; reutilizar el patrón de `ConfusionMatrix` para evitar duplicar tonos.
- [x] `src/components/reports/ReportBadge.tsx` → `frontend2/src/components/reports/ReportBadge.tsx`
- [x] `src/components/reports/ReportFilters.tsx` → `frontend2/src/components/reports/ReportFilters.tsx`
- [x] `src/components/reports/ReportSelectFilter.tsx` → `frontend2/src/components/reports/ReportSelectFilter.tsx`
- [x] `src/components/reports/RunProcessBadge.tsx` → `frontend2/src/components/reports/RunProcessBadge.tsx`
- [ ] `src/components/reports/ScientificArtifact.tsx` → `frontend2/src/components/reports/ScientificArtifact.tsx`
- [x] `src/components/reports/ScientificParameters.tsx` → `frontend2/src/components/reports/ScientificParameters.tsx`
- [ ] `src/components/reports/Stage2PublicationPanel.tsx` → `frontend2/src/components/reports/Stage2PublicationPanel.tsx`
- [ ] `src/components/stage2/Stage2EnablementModal.tsx` → `frontend2/src/components/stage2/Stage2EnablementModal.tsx`
- [x] `src/components/ui/StatusPill.tsx` → `frontend2/src/components/ui/StatusPill.tsx` — Primitiva aislada; migrar primero porque la usan 12 componentes.
- [ ] `src/hooks/useComparisonSelection.tsx` → `frontend2/src/hooks/useComparisonSelection.tsx`

### Onda 2 — Features (dependen de la onda 1) — 15 componente(s)

- [ ] `src/components/deployments/ActiveProductionModel.tsx` → `frontend2/src/components/deployments/ActiveProductionModel.tsx`
- [ ] `src/components/deployments/ActiveStage2Model.tsx` → `frontend2/src/components/deployments/ActiveStage2Model.tsx`
- [ ] `src/components/deployments/DeploymentReviewPanel.tsx` → `frontend2/src/components/deployments/DeploymentReviewPanel.tsx`
- [ ] `src/components/model-architecture/MathFunctionPanel.tsx` → `frontend2/src/components/model-architecture/MathFunctionPanel.tsx`
- [ ] `src/components/navigation/UserMenu.tsx` → `frontend2/src/components/navigation/UserMenu.tsx` — 1 estilo inline para el dropdown. Convertir a utilities y `--menu-height` si sigue siendo dinámico.
- [ ] `src/components/reports/AssessmentEvaluationCard.tsx` → `frontend2/src/components/reports/AssessmentEvaluationCard.tsx`
- [ ] `src/components/reports/AssessmentExplanationCard.tsx` → `frontend2/src/components/reports/AssessmentExplanationCard.tsx`
- [ ] `src/components/reports/AssessmentExplanationDetail.tsx` → `frontend2/src/components/reports/AssessmentExplanationDetail.tsx`
- [ ] `src/components/reports/AutoAnalysisBadge.tsx` → `frontend2/src/components/reports/AutoAnalysisBadge.tsx`
- [ ] `src/components/reports/ComparisonPython.tsx` → `frontend2/src/components/reports/ComparisonPython.tsx`
- [ ] `src/components/reports/LegacyArtifactMedia.tsx` → `frontend2/src/components/reports/LegacyArtifactMedia.tsx`
- [ ] `src/components/reports/LineageBadge.tsx` → `frontend2/src/components/reports/LineageBadge.tsx`
- [ ] `src/components/reports/UnlinkedRunsSection.tsx` → `frontend2/src/components/reports/UnlinkedRunsSection.tsx`
- [ ] `src/components/reports/XAIComparisonViewer.tsx` → `frontend2/src/components/reports/XAIComparisonViewer.tsx`
- [ ] `src/components/reports/XAIOverlayView.tsx` → `frontend2/src/components/reports/XAIOverlayView.tsx`

### Onda 3 — Layouts y composiciones — 35 componente(s)

- [ ] `src/components/explainability/CaseExplainabilityView.tsx` → `frontend2/src/components/explainability/CaseExplainabilityView.tsx`
- [ ] `src/components/model-architecture/ActivationTracePanel.tsx` → `frontend2/src/components/model-architecture/ActivationTracePanel.tsx` — 3 estilos inline y 45 utilities huérfanas; SVG con `stroke-dashoffset`. Convertir el trace en utilities y keyframes `--animate-trace`.
- [ ] `src/components/model-architecture/ArchitectureDetail.tsx` → `frontend2/src/components/model-architecture/ArchitectureDetail.tsx`
- [ ] `src/components/model-architecture/ArchitecturePanel.tsx` → `frontend2/src/components/model-architecture/ArchitecturePanel.tsx`
- [ ] `src/components/model-training/TrainingHistory.tsx` → `frontend2/src/components/model-training/TrainingHistory.tsx` — Heatmap dibujado en `<canvas>` con colores calculados en JS. Tailwind no interviene en la pintura: se migra el wrapper y se centralizan los colores del heatmap en el theme.
- [ ] `src/components/navigation/AppSidebar.tsx` → `frontend2/src/components/navigation/AppSidebar.tsx` — Colapso con `--sidebar-transition-duration` y `transform`. Mapear a `transition-[width,transform] duration-...` y mover la variable a `--sidebar-width` en el theme.
- [ ] `src/components/reports/AssessmentComparison.tsx` → `frontend2/src/components/reports/AssessmentComparison.tsx`
- [ ] `src/components/reports/AssessmentXAI.tsx` → `frontend2/src/components/reports/AssessmentXAI.tsx`
- [ ] `src/components/reports/ComparisonRunCard.tsx` → `frontend2/src/components/reports/ComparisonRunCard.tsx`
- [ ] `src/components/reports/ConsensusSamplesTable.tsx` → `frontend2/src/components/reports/ConsensusSamplesTable.tsx` — Bloqueado: material-react-table + `MRT_Localization_ES` + MUI ThemeProvider. Reescribir con `DataTable` (server-side pagination ya implementada en la capa de datos).
- [ ] `src/components/reports/GeneratedXAIComparison.tsx` → `frontend2/src/components/reports/GeneratedXAIComparison.tsx`
- [ ] `src/components/reports/RunLineageChildCard.tsx` → `frontend2/src/components/reports/RunLineageChildCard.tsx`
- [ ] `src/components/reports/RunSelectorDialog.tsx` → `frontend2/src/components/reports/RunSelectorDialog.tsx`
- [ ] `src/components/reports/RunSummaryRow.tsx` → `frontend2/src/components/reports/RunSummaryRow.tsx`
- [ ] `src/components/reports/ScientificPreflight.tsx` → `frontend2/src/components/reports/ScientificPreflight.tsx`
- [ ] `src/components/reports/ScientificReport.tsx` → `frontend2/src/components/reports/ScientificReport.tsx` — Combina material-react-table (bloqueado) + 4 gráficos recharts + 30 selectores `.trn-mrt .Mui*`. Migrar la página en dos passes: contenedores Tailwind primero, gráficos después (props), tabla al final con `DataTable`.
- [ ] `src/components/reports/ScientificRepresentations.tsx` → `frontend2/src/components/reports/ScientificRepresentations.tsx`
- [ ] `src/components/reports/TrainingExplanationAttempt.tsx` → `frontend2/src/components/reports/TrainingExplanationAttempt.tsx`
- [ ] `src/components/reports/TrainingRunGroupCard.tsx` → `frontend2/src/components/reports/TrainingRunGroupCard.tsx`
- [ ] `src/components/reports/TrainingRunsTable.tsx` → `frontend2/src/components/reports/TrainingRunsTable.tsx` — Bloqueado: misma dependencia. Reescribir con `DataTable` conservando la jerarquía run → grupo.
- [ ] `src/components/reports/TrainingXAIComparison.tsx` → `frontend2/src/components/reports/TrainingXAIComparison.tsx`
- [ ] `src/main.tsx` → `frontend2/src/main.tsx`
- [ ] `src/pages/CampaignConfiguration.tsx` → `frontend2/src/pages/CampaignConfiguration.tsx` — Grid `1fr 340px` con aside sticky; clases `field` y `campaign-saved` sin definición CSS. Mapear a `grid-cols-[1fr_340px]` + `sticky top-0` y breakpoints `lg:`.
- [ ] `src/pages/CampaignsReport.tsx` → `frontend2/src/pages/CampaignsReport.tsx`
- [ ] `src/pages/ClinicalEvaluation.tsx` → `frontend2/src/pages/ClinicalEvaluation.tsx`
- [ ] `src/pages/Dashboard.tsx` → `frontend2/src/pages/Dashboard.tsx`
- [ ] `src/pages/DatasetBrowser.tsx` → `frontend2/src/pages/DatasetBrowser.tsx`
- [ ] `src/pages/DatasetsModels.tsx` → `frontend2/src/pages/DatasetsModels.tsx`
- [ ] `src/pages/Deployments.tsx` → `frontend2/src/pages/Deployments.tsx`
- [ ] `src/pages/ErrorsLogs.tsx` → `frontend2/src/pages/ErrorsLogs.tsx`
- [ ] `src/pages/Login.tsx` → `frontend2/src/pages/Login.tsx` — Login de entrada: migrar pronto porque define el lenguaje visual del shell.
- [ ] `src/pages/ModelVersions.tsx` → `frontend2/src/pages/ModelVersions.tsx`
- [ ] `src/pages/Stage2ReleaseDetail.tsx` → `frontend2/src/pages/Stage2ReleaseDetail.tsx`
- [ ] `src/pages/Traceability.tsx` → `frontend2/src/pages/Traceability.tsx`
- [ ] `src/pages/UploadedPredictions.tsx` → `frontend2/src/pages/UploadedPredictions.tsx`

### Onda 4 — Páginas completas — 10 componente(s)

- [ ] `src/App.tsx` → `frontend2/src/App.tsx`
- [ ] `src/components/Layout.tsx` → `frontend2/src/components/Layout.tsx` — Shell de la app (app-shell, breadcrumb, datasource selector). Migrar tras sidebar y primitivas.
- [ ] `src/pages/AssessmentDetail.tsx` → `frontend2/src/pages/AssessmentDetail.tsx`
- [ ] `src/pages/CellReview.tsx` → `frontend2/src/pages/CellReview.tsx`
- [ ] `src/pages/Explainability.tsx` → `frontend2/src/pages/Explainability.tsx` — 481 líneas, 51 clases; comparte clases con `smear-analysis-immersive.css`. Reutilizar primitivas migradas (badges, chips, cards).
- [ ] `src/pages/ModelComparison.tsx` → `frontend2/src/pages/ModelComparison.tsx`
- [ ] `src/pages/ModelExplorer.tsx` → `frontend2/src/pages/ModelExplorer.tsx`
- [ ] `src/pages/ModelTraining.tsx` → `frontend2/src/pages/ModelTraining.tsx`
- [ ] `src/pages/RunDetail.tsx` → `frontend2/src/pages/RunDetail.tsx` — 1.180 líneas, 72 clases. Migrar en 4 bloques (header, métricas, artefactos, explicabilidad) para no romper el tracker.
- [ ] `src/pages/Runs.tsx` → `frontend2/src/pages/Runs.tsx`

### Onda 5 — Módulo Frotis v2 (ya Tailwind, se copia tal cual) — 19 componente(s)

- [ ] `src/features/analisis-frotis-v2/AnalisisFrotis2Page.tsx` → `frontend2/src/features/analisis-frotis-v2/AnalisisFrotis2Page.tsx`
- [ ] `src/features/analisis-frotis-v2/components/CellDetailModal.tsx` → `frontend2/src/features/analisis-frotis-v2/components/CellDetailModal.tsx`
- [ ] `src/features/analisis-frotis-v2/components/CellGallery.tsx` → `frontend2/src/features/analisis-frotis-v2/components/CellGallery.tsx`
- [ ] `src/features/analisis-frotis-v2/components/CellMicrograph.tsx` → `frontend2/src/features/analisis-frotis-v2/components/CellMicrograph.tsx`
- [ ] `src/features/analisis-frotis-v2/components/DifferentialSidebar.tsx` → `frontend2/src/features/analisis-frotis-v2/components/DifferentialSidebar.tsx`
- [ ] `src/features/analisis-frotis-v2/components/ExportModal.tsx` → `frontend2/src/features/analisis-frotis-v2/components/ExportModal.tsx`
- [ ] `src/features/analisis-frotis-v2/components/FullFieldView.tsx` → `frontend2/src/features/analisis-frotis-v2/components/FullFieldView.tsx`
- [ ] `src/features/analisis-frotis-v2/components/Header.tsx` → `frontend2/src/features/analisis-frotis-v2/components/Header.tsx`
- [ ] `src/features/analisis-frotis-v2/components/ImageAdjustmentsPopover.tsx` → `frontend2/src/features/analisis-frotis-v2/components/ImageAdjustmentsPopover.tsx`
- [ ] `src/features/analisis-frotis-v2/components/NotesDrawer.tsx` → `frontend2/src/features/analisis-frotis-v2/components/NotesDrawer.tsx`
- [ ] `src/features/analisis-frotis-v2/components/QualityView.tsx` → `frontend2/src/features/analisis-frotis-v2/components/QualityView.tsx`
- [ ] `src/features/analisis-frotis-v2/components/ReportView.tsx` → `frontend2/src/features/analisis-frotis-v2/components/ReportView.tsx`
- [ ] `src/features/analisis-frotis-v2/components/SlideViewer.tsx` → `frontend2/src/features/analisis-frotis-v2/components/SlideViewer.tsx`
- [ ] `src/features/analisis-frotis-v2/components/StandaloneHtmlModal.tsx` → `frontend2/src/features/analisis-frotis-v2/components/StandaloneHtmlModal.tsx` — Bloqueado: incrusta HTML externo de `public/analisis-frotis-v2/`. Solo el overlay y el header del modal se migran; el HTML embebido se conserva como artefacto intacto.
- [ ] `src/features/analisis-frotis-v2/pages/AnalysisAreaPage.tsx` → `frontend2/src/features/analisis-frotis-v2/pages/AnalysisAreaPage.tsx`
- [ ] `src/features/analisis-frotis-v2/pages/FullFieldReviewPage.tsx` → `frontend2/src/features/analisis-frotis-v2/pages/FullFieldReviewPage.tsx`
- [ ] `src/features/analisis-frotis-v2/pages/ReportPage.tsx` → `frontend2/src/features/analisis-frotis-v2/pages/ReportPage.tsx`
- [ ] `src/features/analisis-frotis-v2/pages/ReviewCellsPage.tsx` → `frontend2/src/features/analisis-frotis-v2/pages/ReviewCellsPage.tsx`
- [ ] `src/features/analisis-frotis-v2/pages/SpecimenQualityPage.tsx` → `frontend2/src/features/analisis-frotis-v2/pages/SpecimenQualityPage.tsx`

### Onda 6 — Dominio frotis (🚫 conserva CSS propio, se copia sin conversión) — 12 componente(s)

- [ ] `src/components/cell-review/AuthenticatedCellImage.tsx` → `frontend2/src/components/cell-review/AuthenticatedCellImage.tsx`
- [ ] `src/components/cell-review/CellClassificationAuditModal.tsx` → `frontend2/src/components/cell-review/CellClassificationAuditModal.tsx`
- [ ] `src/components/cell-review/CellGradCamPreview.tsx` → `frontend2/src/components/cell-review/CellGradCamPreview.tsx`
- [ ] `src/components/cell-review/CellImageViewer.tsx` → `frontend2/src/components/cell-review/CellImageViewer.tsx` — `className={`cell-box ${visual.className}${isSelected ? ' is-selected' : ''}`}`: `visual.className` proviene de una función de clasificación. Decisión: que `classificationVisual()` devuelva un token (`--cell-ok`, `--cell-warn`) y aplicarlo con `bg-[var(--cell-ok)]` / `border-[var(--cell-ok)]`.
- [ ] `src/components/cell-review/CellReviewWorkspace.tsx` → `frontend2/src/components/cell-review/CellReviewWorkspace.tsx` — 2.280 líneas y 87 clases; usa `[data-state=…]`, `[data-mobile-tab=…]` y `[aria-selected]`. Tailwind 4 soporta variantes de atributo: `data-[state=approved]:bg-green-100`, `aria-[selected=true]:…`. Migrar por secciones (header, paneles, tabla, modales).
- [ ] `src/components/cell-review/ScientificAnnotations.tsx` → `frontend2/src/components/cell-review/ScientificAnnotations.tsx`
- [ ] `src/components/cell-review/SmearAnalysisImmersiveView.tsx` → `frontend2/src/components/cell-review/SmearAnalysisImmersiveView.tsx`
- [ ] `src/components/cell-review/SmearAnalysisResultsView.tsx` → `frontend2/src/components/cell-review/SmearAnalysisResultsView.tsx`
- [ ] `src/components/cell-review/SmearCaseHeader.tsx` → `frontend2/src/components/cell-review/SmearCaseHeader.tsx`
- [ ] `src/pages/SmearAnalysisHistory.tsx` → `frontend2/src/pages/SmearAnalysisHistory.tsx`
- [ ] `src/pages/SmearUpload.tsx` → `frontend2/src/pages/SmearUpload.tsx`
- [ ] `src/pages/SmearWorkflow.tsx` → `frontend2/src/pages/SmearWorkflow.tsx` — 1.264 líneas con `[data-mode="setup"]` y `[data-mobile-tab]`. Mismo patrón: variantes `data-[…]`. Separar el scroll de actividad (`workflow-activity-scroll`, hoy sin definición CSS) con `overflow-y-auto`.

## 6. Criterios de verificación por componente

1. El archivo migrado **no importa ningún `.css`** propio.
2. No quedan clases que no existan en Tailwind ni en el `@theme`.
3. `npm run build` en `frontend2` compila sin errores (`tsc --noEmit`).
4. La lógica (props, estado, API, routing) es idéntica a la original.
5. Tras cada migración: actualizar estado ⬜→✅, el % y el log de §7.

### Verificación final del subsistema

```bash
# 1. No debe existir ningún CSS con reglas propias fuera del theme
find frontend2/src -name '*.css' -exec grep -L '@import "tailwindcss"' {} +
# 2. No debe quedar ninguna importación de librerías de estilos
grep -rn '@mui\|material-react-table\|styled-components\|\.module\.css' frontend2/src
# 3. El frontend original permanece intacto
# (frontend/ nunca se toca; su checksum no cambia)
```

---

## 7. Progreso

```markdown
## Progreso

| Métrica | Valor |
|---------|-------|
| Total componentes | 124 |
| Migrados | 35 |
| Pendientes | 77 |
| Excepciones de alcance (🚫, conservan CSS propio) | 12 |
| % completado | 35/112 componentes reales a convertir = 31.3% (35/124 del inventario = 28.2%) |
```

> **Matiz honesto:** de los 35 ✅, 19 son el módulo `analisis-frotis-v2` (E4: copia textual, ya usa Tailwind) y 16 son primitivas genuinely reescritas con utilities. Los 12 🚫 del dominio frotis no se convierten: viven en `src/styles/frotis-workflow.css`.

### Log

- **2026-11-10** — Inventario inicial completado: 124 componentes clasificados, 14 archivos CSS analizados (16.879 líneas), tokens extraídos y propuesta de `@theme`, 6 componentes bloqueados, orden de migración en 5 ondas derivado del grafo de dependencias. No se modificó nada en `frontend/`.
- **2026-11-10** — Onda 0 (infraestructura): `package.json`, `vite.config.ts`, tsconfigs, `index.html`, `Dockerfile`, `postcss.config.cjs`, `src/styles.css` con `@theme`, copia de types/utils/services/config/hooks/assets/router/tests/public, y `src/styles/frotis-workflow.css` (E3).
- **2026-11-11** — Onda 1 (16/35 primitivas): DomainBadge, Loading, MetricCard, StatusBadge, StatusPill, ReportBadge, RunProcessBadge, MetricChip, ScientificParameters, ComparisonEligibilityStatus, ReportFilters, ReportSelectFilter, ProductionStepIndicator, ModelApprovalModal, TechnicalContractModal, ProductionActivationModal. Cada clase original se tradujo a utilities literales; los tonos dinámicos se resolvieron con mapas de clases (`TONE`, `LEVEL`, `STATE_CLASS`). `styles.css` ganó los tokens que faltaban (`--color-chip*`, `--radius-panel/step`, `--shadow-panel`, triadas warn-2/info/neutral).
- **2026-11-11** — Corrección de andamiaje: Tailwind 4 exige `@tailwindcss/postcss`; se instaló y `postcss.config.cjs` ahora usa `{'@tailwindcss/postcss': {}}`. Verificado: el dev server compila 76 KB de CSS y genera `rounded-panel`, `bg-surface`, `shadow-panel`, `text-metric`, etc.
- **2026-11-11** — Vista previa aislada: `frontend2/preview.html` + `src/preview.tsx` (harness temporal de desarrollo, no forma parte de la migración) para ver el tema y las primitivas en el navegador sin tocar `frontend/`. Ajuste de contraste (verificado con DOM real): nuevos tokens de superficie `--surface-value`, `--step-complete-fg`, `--step-current-fg`, `--step-pending-fg` → utilities `text-value`, `text-step-complete/current/pending`, `text-fg-strong`. Valores de métricas: #1f7a45 (claro) / #7bd6a4 (oscuro, 9.4:1); `#1f7a45` sobre el panel lab daría solo 3.1:1. Steps 3 y 4: #27324a / #dae2fd. Pill `neutral` vuelve a `bg-neutral-soft text-neutral-fg` (igual que `--ds-status-neutral-*`). Pendiente en Onda 0: `main.tsx`/`App.tsx` (se crean con la Onda 3) y `.env.example`.
