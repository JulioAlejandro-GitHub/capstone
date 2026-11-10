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
| `src/components/DomainBadge.tsx` | DomainBadge | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/Layout.tsx` | Layout | layout | CSS global: styles.css, tokens.css | media | AppSidebar | ⬜ |
| `src/components/Loading.tsx` | Loading | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/MetricCard.tsx` | MetricCard | primitiva | utilities huérfanas (sin CSS que las defina) | baja | — | ⬜ |
| `src/components/RouteState.tsx` | RouteState | primitiva | CSS global: styles.css, tokens.css | baja | — | ⬜ |
| `src/components/ScientificResults.tsx` | ScientificResults | feature | utilities huérfanas (sin CSS que las defina) | baja | — | ⬜ |
| `src/components/StatusBadge.tsx` | StatusBadge | primitiva | CSS global: styles.css | baja | — | ⬜ |

### 2.2 `components/ui` — 1 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/ui/StatusPill.tsx` | StatusPill | primitiva | CSS global: styles.css | baja | — | ⬜ |

### 2.3 `components/navigation` — 3 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/navigation/AppSidebar.tsx` | AppSidebar | layout | CSS global: styles.css, tokens.css | media | NavigationIcon, UserMenu | ⬜ |
| `src/components/navigation/NavigationIcon.tsx` | NavigationIcon | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/navigation/UserMenu.tsx` | UserMenu | feature | CSS global: styles.css | baja | auth | ⬜ |

### 2.4 `components/cell-review` — 9 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/cell-review/AuthenticatedCellImage.tsx` | AuthenticatedCellImage | feature | CSS global: styles.css | alta | — | ⬜ |
| `src/components/cell-review/CellClassificationAuditModal.tsx` | CellClassificationAuditModal | feature | CSS global: styles.css | baja | CaseExplainabilityView | ⬜ |
| `src/components/cell-review/CellGradCamPreview.tsx` | CellGradCamPreview | feature | CSS global: smear-analysis-immersive.css, tokens.css | media | AuthenticatedCellImage | ⬜ |
| `src/components/cell-review/CellImageViewer.tsx` | CellImageViewer | feature | CSS global: smear-analysis-immersive.css, styles.css | alta | AuthenticatedCellImage | ⬜ |
| `src/components/cell-review/CellReviewWorkspace.tsx` | CellReviewWorkspace | feature | CSS global: smear-analysis-immersive.css, styles.css | alta | AuthenticatedCellImage, CellClassificationAuditModal, CellGradCamPreview, CellImageViewer, ScientificAnnotations | ⬜ |
| `src/components/cell-review/ScientificAnnotations.tsx` | ScientificAnnotations | feature | CSS global: smear-analysis-immersive.css, styles.css | media | — | ⬜ |
| `src/components/cell-review/SmearAnalysisImmersiveView.tsx` | SmearAnalysisImmersiveView | layout | CSS global: styles.css | media | CellReviewWorkspace, ScientificAnnotations | ⬜ |
| `src/components/cell-review/SmearAnalysisResultsView.tsx` | SmearAnalysisResultsView | feature | CSS global: styles.css | baja | SmearAnalysisImmersiveView | ⬜ |
| `src/components/cell-review/SmearCaseHeader.tsx` | SmearCaseHeader | feature | CSS global: styles.css, smear-analysis-immersive.css | media | — | ⬜ |

### 2.5 `components/deployments` — 7 archivo(s)

| Ruta | Nombre | Tipo | Estilos actuales | Complejidad | Dependencias | Estado |
|---|---|---|---|---|---|---|
| `src/components/deployments/ActiveProductionModel.tsx` | ActiveProductionModel | feature | CSS global: styles.css, tokens.css | baja | StatusBadge | ⬜ |
| `src/components/deployments/ActiveStage2Model.tsx` | ActiveStage2Model | feature | CSS global: styles.css, report-components.css | baja | StatusBadge | ⬜ |
| `src/components/deployments/DeploymentReviewPanel.tsx` | DeploymentReviewPanel | feature | CSS global: styles.css, report-components.css | media | Loading, ProductionStepIndicator, StatusBadge | ⬜ |
| `src/components/deployments/ModelApprovalModal.tsx` | ModelApprovalModal | feature | CSS global: styles.css | baja | — | ⬜ |
| `src/components/deployments/ProductionActivationModal.tsx` | ProductionActivationModal | feature | CSS global: styles.css | baja | — | ⬜ |
| `src/components/deployments/ProductionStepIndicator.tsx` | ProductionStepIndicator | feature | utilities huérfanas (sin CSS que las defina) | baja | — | ⬜ |
| `src/components/deployments/TechnicalContractModal.tsx` | TechnicalContractModal | feature | CSS global: styles.css, tokens.css | baja | — | ⬜ |

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
| `src/components/model-training/TrainingScene.tsx` | TrainingScene | feature | CSS global: styles.css | alta | — | ⚠️ |

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
| `src/components/reports/ComparisonEligibilityStatus.tsx` | ComparisonEligibilityStatus | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/reports/ComparisonPython.tsx` | ComparisonPython | feature | CSS global: scc-comparison.css, ds-primitives.css | baja | NavigationIcon | ⬜ |
| `src/components/reports/ComparisonRunCard.tsx` | ComparisonRunCard | feature | CSS global: report-components.css, scc-comparison.css | baja | ComparisonPython, StatusPill | ⬜ |
| `src/components/reports/ConsensusSamplesTable.tsx` | ConsensusSamplesTable | feature | CSS global: scc-comparison.css, report-components.css | media | ComparisonPython | ⚠️ |
| `src/components/reports/DatasetIntegrity.tsx` | DatasetIntegrity | feature | CSS global: scc-comparison.css, ds-primitives.css | media | — | ⬜ |
| `src/components/reports/GeneratedXAIComparison.tsx` | GeneratedXAIComparison | feature | CSS global: styles.css | baja | XAIComparisonViewer, auth | ⬜ |
| `src/components/reports/LegacyArtifactMedia.tsx` | LegacyArtifactMedia | feature | CSS global: styles.css | baja | AuthenticatedCellImage | ⬜ |
| `src/components/reports/LineageBadge.tsx` | LineageBadge | primitiva | CSS global: styles.css | baja | ReportBadge | ⬜ |
| `src/components/reports/MetricChip.tsx` | MetricChip | primitiva | utilities huérfanas (sin CSS que las defina) | baja | — | ⬜ |
| `src/components/reports/MiniConfusionMatrix.tsx` | MiniConfusionMatrix | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/reports/ReportBadge.tsx` | ReportBadge | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/reports/ReportFilters.tsx` | ReportFilters | primitiva | CSS global: report-components.css, tokens.css | baja | — | ⬜ |
| `src/components/reports/ReportSelectFilter.tsx` | ReportSelectFilter | primitiva | CSS global: report-components.css, tokens.css | baja | — | ⬜ |
| `src/components/reports/RunLineageChildCard.tsx` | RunLineageChildCard | primitiva | CSS global: styles.css | media | LineageBadge, MetricChip, MiniConfusionMatrix, ReportBadge, RunProcessBadge, StatusBadge | ⬜ |
| `src/components/reports/RunProcessBadge.tsx` | RunProcessBadge | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/reports/RunSelectorDialog.tsx` | RunSelectorDialog | feature | CSS global: scc-comparison.css, report-components.css | baja | TrainingRunGroupCard, TrainingRunsTable | ⬜ |
| `src/components/reports/RunSummaryRow.tsx` | RunSummaryRow | primitiva | CSS global: report-components.css, scc-comparison.css | media | AutoAnalysisBadge, CommandChips, MetricChip, MiniConfusionMatrix, NavigationIcon, RunProcessBadge, ScientificParameters, StatusBadge | ⬜ |
| `src/components/reports/ScientificArtifact.tsx` | ScientificArtifact | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/reports/ScientificParameters.tsx` | ScientificParameters | primitiva | CSS global: styles.css | baja | — | ⬜ |
| `src/components/reports/ScientificPreflight.tsx` | ScientificPreflight | feature | CSS global: scc-comparison.css, report-components.css | alta | AnalysisWorkspace, ArchitecturePanel, ComparisonPython, DatasetIntegrity, ScientificReport, ScientificRepresentations, auth | ⬜ |
| `src/components/reports/ScientificReport.tsx` | ScientificReport | feature | CSS global: scc-comparison.css, report-components.css | alta | AnalysisWorkspace, AssessmentXAI, ComparisonPython, ConsensusSamplesTable, GeneratedXAIComparison | ⚠️ |
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
| `src/pages/SmearAnalysisHistory.tsx` | SmearAnalysisHistory | página | CSS global: styles.css, tokens.css | media | SmearWorkflow | ⬜ |
| `src/pages/SmearUpload.tsx` | SmearUpload | página | CSS global: styles.css, tokens.css | alta | — | ⬜ |
| `src/pages/SmearWorkflow.tsx` | SmearWorkflow | página | CSS global: styles.css, smear-analysis-immersive.css | alta | SmearAnalysisImmersiveView, SmearCaseHeader, SmearUpload, auth | ⬜ |
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
| `src/features/analisis-frotis-v2/components/StandaloneHtmlModal.tsx` | StandaloneHtmlModal | feature | Tailwind utilities + @theme (frotis-v2) | alta | — | ⚠️ |
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
## 3. Design tokens actuales → propuesta `@theme`

La fuente de verdad es `src/styles/tokens.css` (174 líneas) con tres capas: **primitivos**, **semánticos por superficie** (`workbench` claro / `lab` oscuro) y **aliases legacy** (`--color-*` tipo Material). El módulo Frotis v2 tiene su propio `@theme` (`tokens_frotis_v2.css`) que ya es Tailwind 4 y se conserva.

### 3.1 Color — primitivos

| Token original | Valor | Token `@theme` | Utility |
|---|---|---|---|
| `--ds-slate-0` | `#ffffff` | `--color-surface` | `bg-surface` |
| `--ds-slate-25` | `#f8faff` | `--color-subtle` | `bg-subtle` |
| `--ds-slate-50` | `#f6f7fb` | `--color-canvas` | `bg-canvas` |
| `--ds-slate-100` | `#eef1f7` | `--color-hover` | `hover:bg-hover` |
| `--ds-slate-200` | `#e3e7f0` | `--color-border` | `border-border` |
| `--ds-slate-300` | `#cfd7e8` | `--color-border-strong` | `border-border-strong` |
| `--ds-slate-400` | `#8a95ad` | `--color-muted-2` | `text-muted-2` |
| `--ds-slate-500` | `#62708f` | `--color-muted` | `text-muted` |
| `--ds-slate-600` | `#465574` | `--color-ink-2` | `text-ink-2` |
| `--ds-slate-700` | `#27324a` | `--color-ink` | `text-ink` |
| `--ds-slate-900` | `#172033` | `--color-ink-strong` | `text-ink-strong` |
| `--ds-night-0` | `#060e20` | `--color-night-0` | `bg-night-0` |
| `--ds-night-50` | `#0b1326` | `--color-night-50` | `bg-night-50` |
| `--ds-night-100` | `#131b2e` | `--color-night-100` | `bg-night-100` |
| `--ds-night-200` | `#171f33` | `--color-night-200` | `bg-night-200` |
| `--ds-night-300` | `#222a3d` | `--color-night-300` | `bg-night-300` |
| `--ds-night-400` | `#2d3449` | `--color-night-400` | `bg-night-400` |
| `--ds-night-500` | `#3c494e` | `--color-night-500` | `border-night-500` |
| `--ds-night-600` | `#859399` | `--color-night-600` | `text-night-600` |
| `--ds-night-700` | `#bbc9cf` | `--color-night-700` | `text-night-700` |
| `--ds-night-800` | `#dae2fd` | `--color-night-800` | `text-night-800` |
| `--ds-neutral-950` | `#121212` | `--color-viewer` | `bg-viewer` |
| `--ds-blue-600/500/100` | `#284a9c / #315caa / #eaf0ff` | `--color-accent`, `--color-accent-2`, `--color-accent-soft` | `bg-accent`, `text-accent` |
| `--ds-cyan-300/400` | `#a4e6ff / #4cd6ff` | `--color-primary`, `--color-primary-strong` | `bg-primary` |
| `--ds-green-700/100/300` | `#17653b / #e7f8ef / #4edea3` | `--color-ok`, `--color-ok-soft`, `--color-ok-strong` | `bg-ok-soft text-ok` |
| `--ds-amber-700/100/300` | `#8a5a00 / #fff6df / #ffd5a5` | `--color-warn`, `--color-warn-soft`, `--color-warn-strong` | `bg-warn-soft text-warn` |
| `--ds-red-700/100/300` | `#9a2323 / #fdecec / #ffb4ab` | `--color-danger`, `--color-danger-soft`, `--color-danger-strong` | `bg-danger-soft text-danger` |
| `--ds-violet-700/100/300` | `#4b3a8f / #efecfb / #c9bfff` | `--color-blocked`, `--color-blocked-soft`, `--color-blocked-strong` | `bg-blocked-soft text-blocked` |

### 3.2 Color — semánticos por superficie (decisión no trivial)

`tokens.css` define variables distintas según `[data-surface="workbench"]` (claro) o `[data-surface="lab"]` (oscuro). Tailwind no puede tener dos `@theme`: la solución es **un `@theme inline` que referencie variables CSS cambiantes**.

```css
@theme inline {
  --color-canvas: var(--surface-canvas);
  --color-surface: var(--surface-panel);
  --color-subtle: var(--surface-subtle);
  --color-fg: var(--fg-default);
  --color-muted: var(--fg-muted);
  --color-border: var(--border-default);
}
```

```css
[data-surface="workbench"] { --surface-canvas:#f6f7fb; --surface-panel:#fff; --fg-default:#172033; --fg-muted:#62708f; --border-default:#e3e7f0; }
[data-surface="lab"]       { --surface-canvas:#0b1326; --surface-panel:#171f33; --fg-default:#dae2fd; --fg-muted:#bbc9cf; --border-default:#3c494e; --surface-viewer:#121212; }
```

Resultado: `bg-canvas`, `bg-surface`, `text-fg`, `border-border` funcionan en ambos temas sin duplicar clases.

### 3.3 Tipografía, spacing, radius y sombras

| Original | Valor | `@theme` | Utility resultante |
|---|---|---|---|
| `--ds-text-xs` | 12px | `--text-xs: 12px` | `text-xs` |
| `--ds-text-sm` | 13px | `--text-sm: 13px` | `text-sm` |
| `--ds-text-lg` | 16px | `--text-lg: 16px` | `text-lg` |
| `--ds-text-title` | 30px | `--text-title: 30px` | `text-title` |
| `--ds-text-metric` | 26px | `--text-metric: 26px` | `text-metric` |
| `--ds-line-height` | 1.45 | `--leading-ui: 1.45` | `leading-[var(--leading-ui)]` |
| `--ds-weight-medium/semibold/bold` | 500/600/700 | Tailwind nativo | `font-medium`, `font-semibold`, `font-bold` |
| `--ds-font-mono` | SFMono/Consolas | `--font-mono` | `font-mono` |
| `--ds-space-1…6` | 2/4/8/12/16/24 | `--spacing: 4px` (p-1=4, p-2=8, p-3=12, p-4=16, p-6=24) | `p-2`, `gap-4`; el caso de 2px → `p-0.5` |
| `--ds-gap-section` | 22px | `--space-section: 22px` | `gap-[var(--space-section)]` |
| `--ds-gap-subsection` | 24px | `--space-subsection: 24px` | `gap-[var(--space-subsection)]` |
| `--ds-pad-section` | 16px | `--space-panel: 16px` | `p-[var(--space-panel)]` |
| `--ds-pad-control-y/x` | 7/11px | `--pad-control: 7px 11px` | `py-[7px] px-[11px]` (componente `Button`) |
| `--ds-page-padding` | 28px | `--space-page: 28px` | `p-[var(--space-page)]` |
| `--ds-border-width` | 1px | Tailwind nativo | `border` |
| `--ds-accent-width` | 3px | `--accent-w: 3px` | `border-l-[3px]` |
| `--ds-radius-sm/md/lg` | 4/6/8 | `--radius-sm/md/lg` | `rounded-sm`, `rounded-md`, `rounded-lg` |
| `--ds-radius-card` | 14px | `--radius-card: 14px` | `rounded-card` |
| `--ds-radius-modal` | 16px | `--radius-modal: 16px` | `rounded-modal` |
| `--ds-radius-pill` | 999px | `--radius-pill: 999px` | `rounded-pill` |
| `--ds-shadow-card` | `0 7px 20px rgba(18,26,47,.045)` | `--shadow-card` | `shadow-card` |
| `--ds-shadow-modal` | `0 28px 80px rgba(0,0,0,.28)` | `--shadow-modal` | `shadow-modal` |

### 3.4 Tokens Frotis v2 (ya Tailwind: se fusionan, no se traducen)

El módulo Frotis v2 define ~100 tokens (`--frotis-v2-*`) con `@theme inline` y una paleta propia (rosa/violeta de tinción, `#4d58a4`, `#d9b6c9`, densidad `#af5d85`). Decisiones:
- Mantener la paleta del visor como namespace `frotis-*` dentro del `@theme` global (no hay conflicto con `slate`/`night`).
- Eliminar el paso de generación: `scripts/generate-frotis-css.cjs` scopea todo a `.frotis-v2` para no chocar con el CSS del host. En `frontend2` no existe host CSS → **Tailwind se carga directo** y se borra `module.css` y el script.
- Los `z-index` (`--frotis-v2-z-modal: 50`) pasan a utilities `z-50`, `z-30`, `z-10`.

### 3.5 Archivo de referencia para `frontend2`

```css
/* frontend2/src/styles.css — único archivo de estilos */
@import "tailwindcss";

@theme {
  /* primitivos de color (ver 3.1) */
  --color-surface: #ffffff; --color-subtle: #f8faff; --color-canvas: #f6f7fb;
  --color-night-50: #0b1326; --color-night-200: #171f33; --color-viewer: #121212;
  --color-accent: #284a9c; --color-primary: #a4e6ff;
  --color-ok: #17653b; --color-ok-soft: #e7f8ef;
  --color-warn: #8a5a00; --color-warn-soft: #fff6df;
  --color-danger: #9a2323; --color-danger-soft: #fdecec;
  --color-blocked: #4b3a8f; --color-blocked-soft: #efecfb;
  /* tipografía */
  --text-title: 30px; --text-metric: 26px; --text-lg: 16px; --text-sm: 13px; --text-xs: 12px;
  --font-mono: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  /* escala */
  --spacing: 4px;
  --radius-sm: 4px; --radius-md: 6px; --radius-lg: 8px;
  --radius-card: 14px; --radius-modal: 16px; --radius-pill: 999px;
  --shadow-card: 0 7px 20px rgba(18,26,47,.045);
  --shadow-modal: 0 28px 80px rgba(0,0,0,.28);
  /* animaciones */
  --animate-smear-spin: smear-spin 1.2s linear infinite;
  --animate-smear-scan: smear-scan 2.4s ease-in-out infinite;
  --animate-panel-in: panel-in 240ms ease-out;
  --animate-step-in: step-in 180ms ease-out;
  --animate-dialog-in: dialog-in 200ms ease-out;
  --animate-xai-pulse: xai-pulse 2s ease-in-out infinite;
}

@theme inline {
  --color-canvas: var(--surface-canvas); --color-surface: var(--surface-panel);
  --color-fg: var(--fg-default); --color-muted: var(--fg-muted); --color-border: var(--border-default);
}

[data-surface="workbench"] { --surface-canvas:#f6f7fb; --surface-panel:#fff; --fg-default:#172033; --fg-muted:#62708f; --border-default:#e3e7f0; }
[data-surface="lab"]       { --surface-canvas:#0b1326; --surface-panel:#171f33; --fg-default:#dae2fd; --fg-muted:#bbc9cf; --border-default:#3c494e; --surface-viewer:#121212; }
```

---

## 4. Casos especiales

### 4.1 Estilos dinámicos (props → estilos)

**57 componentes** construyen clases con interpolación. Los patrones detectados:

| Patrón | Ejemplo (origen) | Receta Tailwind |
|---|---|---|
| Modificador por estado | `className={`status status-${normalized}`}` (`StatusBadge`) | objeto `TONES = {ok:'bg-ok-soft text-ok', warn:'bg-warn-soft text-warn', …}` → clases literales |
| Modificador por prioridad | `clinical-confusion__cell--${result}${priority}` (`ConfusionMatrix`) | mapa de 4 combinaciones literales; jamás concatenar nombres |
| Estado por atributo | `[data-state="approved"]`, `[data-mobile-tab="cells"]`, `[data-mode="setup"]`, `[data-density="compact"]` (≈72 selectores) | `data-[state=approved]:bg-ok-soft`, `data-[density=compact]:text-xs` |
| Atributos ARIA | `[aria-selected="true"]`, `[aria-pressed="true"]` | `aria-[selected=true]:…` |
| Valor numérico → tamaño | `style={{width: `${minimapWidth}px`}}`, `style={{width: `${scaleBar.widthPx}px`}}` (`SlideViewer`) | `style={{'--w': w}}` + `w-[var(--w)]` |
| Posición/zoom calculado | `transform: translate(...) scale(zoom)` (`SlideViewer`, `CellImageViewer`) | variables `--tx/--ty/--zoom` + `translate-[var(--tx)] scale-[var(--zoom)]` |
| Color por clase de célula | `classificationVisual()` devuelve `visual.className` (`CellImageViewer`, 62 clases) | la función devuelve un token (`--cell-ok`, `--cell-warn`) aplicado con `bg-[var(--cell-ok)]` |

### 4.2 Keyframes (12) → `--animate-*`

| Origen | Animación | Qué hace | Mapeo |
|---|---|---|---|
| `styles.css` | `smear-workflow-spin` | spinner del workflow de frotis | `--animate-smear-spin: smear-workflow-spin 1.2s linear infinite` + `@keyframes` en el theme |
| `styles.css` | `smear-scan` | barrido de la imagen | `animate-smear-scan` |
| `styles.css` | `smear-quality-pulse` | pulso de calidad | `animate-smear-pulse` |
| `styles.css` | `smear-workflow-panel-in` | entrada de panel | `animate-panel-in` |
| `report-components.css` | `run-promotion-spin` | promoción de run a Stage 2 | `animate-run-spin` |
| `report-components.css` | `stage2-panel-in` | entrada de panel Stage 2 | `animate-stage2-in` |
| `model-explorer.css` | `mx-progress` | barra de progreso (scaleX) | `animate-progress` + `--animate-*` con keyframes scaleX |
| `model-explorer.css` | `mx-step-in` | entrada de paso (opacity+translateY) | `animate-step-in` |
| `model-explorer.css` | `mx-fade` | fade de fondo | `animate-fade` |
| `model-explorer.css` | `mx-dialog-in` | entrada de diálogo (scale .97) | `animate-dialog-in` |
| `scc-comparison.css` | `xai-pulse` | pulso XAI (50% opacity) | `animate-xai-pulse` |
| `frotis module.css (generado)` | `frotis-v2-pulse` | pulso del visor Frotis v2 | ya cubierto por `animate-pulse` de Tailwind |

Nota: Tailwind 4 requiere declarar los `@keyframes` en el mismo archivo de estilos; se conservan los 11 originales (el de Frotis v2 se reemplaza por `animate-pulse` nativo). Los `prefers-reduced-motion` (5 bloques en `styles.css`) se replican con `motion-reduce:animate-none` / `motion-reduce:transition-none`.

### 4.3 Selectores complejos que no tienen equivalencia directa

| Tipo | Cantidad | Ejemplo | Decisión |
|---|---|---|---|
| `::before` / `::after` | 40 en host | `mt-halo`, indicadores de célula, rayas de separación | `before:`/`after:` utilities con `content-['']` |
| `> * + *` (hermanos) | ~30 | `.ds-stack-divided > * + *`, `.ds-list-group > * + *` | wrapper con `divide-y divide-border` o `*:has(+ *)` |
| `:has()` | 2 | `.trn-select-cell:has(> svg)` | se elimina: el icono se renderiza como prop |
| `[colspan]` sobre celdas MUI | 1 | `.trn-row > .MuiTableCell-body[colspan="4"]` | desaparece con la tabla propia |
| `!important` | 39 | overrides de sidebar y badges | se eliminan: Tailwind resuelve por especificidad de layer |
| `@media` | ~60 en host | breakpoints 1024/768/640 px | `sm:` `md:` `lg:` `xl:`; revisar mapa breakpoint→utility |
| `prefers-reduced-motion` | 5 bloques | desactiva animaciones | `motion-reduce:` variants |

### 4.4 Librerías con estilos propios (deben desaparecer)

| Librería | Dónde | Por qué bloquea | Plan |
|---|---|---|---|
| `material-react-table` | `ConsensusSamplesTable.tsx`, `TrainingRunsTable.tsx` | Trae sus propios CSS y su ThemeProvider MUI; ~30 selectores `.Mui*` lo ajustan | Reescribir como `DataTable` Tailwind; la lógica de paginación/filtros ya está en los hooks y no cambia |
| `@mui/material` | `ThemeProvider` en las dos tablas | estilos MUI | eliminar la dependencia |
| `@mui/icons-material` | 2 iconos | iconografía MUI | sustituir por `lucide-react` (ya presente) |
| `@mui/x-date-pickers` | declarado, sin uso detectado | — | no se instala en `frontend2` |
| `recharts` | 3 componentes | estilo por props/attrs SVG; el CSS interviene `.recharts-scatter-symbol` | se mantiene, pero con **cero** CSS: colores, ejes y tooltips pasan a props |

### 4.5 Artefactos HTML externos

`public/analisis-frotis-v2/visor-standalone.html`, `scopio-standalone.html` y `assets/aistudio/*.html` se abren en `StandaloneHtmlModal`. Tienen estilos embebidos ajenos al proyecto. No se migran: **se conservan intactos** y solo el shell del modal pasa a Tailwind (marcado ⚠️).

### 4.6 Renderizado no-CSS (canvas / SVG) — ⚠️ requiere decisión

- `TrainingHistory.tsx`: heat map de células dibujado con `canvas` y colores calculados en JS → Tailwind no puede intervenir; se centralizan los colores en el theme para que el wrapper y la leyenda coincidan.
- `model-architecture/*` y `mathOperations.tsx`: SVG generado (trazas, dasharrays) con `stroke-dashoffset` animado → utilities + keyframes en el theme.

### 4.7 Clases huérfanas (sin definición CSS) — 41 casos

Estas clases hoy **no tienen efecto**: aparecen en el markup pero ningún CSS las define. Se convierten en utilities reales durante la migración (no es una pérdida visual, es deuda heredada). Ejemplos: `mt-root`, `mt-halo`, `detail-actions`, `modal-card`, `primary`, `secondary`, `training-card`, `run-detail-metrics`, `workflow-activity-scroll`, `campaign-saved`, `field`, `zoom`.

### 4.8 Tests acoplados al CSS (hay que actualizarlos)

| Test | Qué verifica | Impacto |
|---|---|---|
| `tests/cell-classification-workflow.test.mjs` | lee `src/styles.css` y busca selectores | reescribir contra clases Tailwind o contra el theme |
| `tests/cell-review-workspace.test.mjs` | lee `styles.css` | idem |
| `tests/deployments-inline-review.test.mjs` | `styles.css` + `api.ts` | idem |
| `tests/executions-lazy-loading.test.mjs` / `executions-promotion.test.mjs` | `report-components.css` | idem |
| `tests/model-ai-navigation.test.mjs` | `styles.css` | idem |
| `tests/run-detail-explainability.test.mjs` | `styles.css` | idem |
| `tests/scc-*.test.mjs` (4) | CSS por dominio | idem |
| `tests/smear-ui-refresh.test.mjs`, `smear-workflow.test.mjs`, `smear-analysis-results-view.test.mjs`, `scientific-review-ui.test.mjs` | selectores de clase | idem |
| `tests/frotis-v2-design-system.test.mjs` | parsea `tokens_frotis_v2.css`, `tailwind.css`, `module.css` | en `frontend2` se evalúa el `@theme` global; el test debe reescribirse |
| `tests/browser/frotis-v2-design.cjs` | Playwright: `toHaveCSS` sobre `--frotis-v2-*` | mantener; ajustar el prefijo si se fusionan tokens |

---
## 5. Orden de migración (de hoja a raíz)

El orden se derivó del grafo de dependencias internas: un componente se migra **después** de todos los que importa. Se agregan dos ondas previas de infraestructura.

### Onda 0 — Infraestructura (antes de cualquier componente)

- [ ] `frontend2/package.json` — React 19 + react-router 7 + lucide + recharts + `tailwindcss` 4; **sin** `@mui/*`, `material-react-table`, `postcss` de generación.
- [ ] `frontend2/vite.config.ts` + `tsconfig.json` — mismos que el origen.
- [ ] `frontend2/src/styles.css` — `@import "tailwindcss"` + `@theme` (§3.5). Único archivo CSS.
- [ ] `frontend2/src/main.tsx` — sin imports de CSS (solo `styles.css` desde el entry global).
- [ ] Copiar `types/`, `utils/`, `services/api.ts`, `config/`, `data/`, `router.ts`, `hooks/`, `assets/` sin cambios.
- [ ] `frontend2/tests/` — portar los tests de lógica (los 17 que leen CSS se adaptan al final).


### Onda 1 — Primitivas (sin dependencias internas) — 39 componente(s)



- [ ] `src/components/ConfusionMatrix.tsx` → `frontend2/src/components/ConfusionMatrix.tsx` — Tiene CSS propio (`ConfusionMatrix.css`, 173 líneas) y modificadores `--${result}${priority}`. Reproducir las 4 combinaciones como mapa de clases; el resto del layout con utilities.
- [ ] `src/components/DataTable.tsx` → `frontend2/src/components/DataTable.tsx` — Base para reemplazar material-react-table: implementar paginación, sort y filtros como props, sin librería.
- [ ] `src/components/DomainBadge.tsx` → `frontend2/src/components/DomainBadge.tsx`
- [ ] `src/components/Loading.tsx` → `frontend2/src/components/Loading.tsx`
- [ ] `src/components/MetricCard.tsx` → `frontend2/src/components/MetricCard.tsx` — Usa utilities huérfanas (`flex`, `text-xs`) que hoy no defina ningún CSS: se convierten en utilities reales de Tailwind, sin pérdida de comportamiento.
- [ ] `src/components/RouteState.tsx` → `frontend2/src/components/RouteState.tsx`
- [ ] `src/components/StatusBadge.tsx` → `frontend2/src/components/StatusBadge.tsx` — Clases `status` + `status-${normalized}` definidas en `styles.css`. Mapeo: objeto `STATUS_TONE = {ok:[...], warning:[...], error:[...]}` que devuelve utilities literales (Tailwind no permite nombres de clase dinámicos).
- [ ] `src/components/model-architecture/mathOperations.tsx` → `frontend2/src/components/model-architecture/mathOperations.tsx`
- [ ] `src/components/navigation/NavigationIcon.tsx` → `frontend2/src/components/navigation/NavigationIcon.tsx`
- [ ] `src/components/reports/CommandChips.tsx` → `frontend2/src/components/reports/CommandChips.tsx`
- [ ] `src/components/reports/ComparisonEligibilityStatus.tsx` → `frontend2/src/components/reports/ComparisonEligibilityStatus.tsx`
- [ ] `src/components/reports/MetricChip.tsx` → `frontend2/src/components/reports/MetricChip.tsx`
- [ ] `src/components/reports/MiniConfusionMatrix.tsx` → `frontend2/src/components/reports/MiniConfusionMatrix.tsx` — Primitiva de reporte; reutilizar el patrón de `ConfusionMatrix` para evitar duplicar tonos.
- [ ] `src/components/reports/ReportBadge.tsx` → `frontend2/src/components/reports/ReportBadge.tsx`
- [ ] `src/components/reports/ReportFilters.tsx` → `frontend2/src/components/reports/ReportFilters.tsx`
- [ ] `src/components/reports/ReportSelectFilter.tsx` → `frontend2/src/components/reports/ReportSelectFilter.tsx`
- [ ] `src/components/reports/RunProcessBadge.tsx` → `frontend2/src/components/reports/RunProcessBadge.tsx`
- [ ] `src/components/reports/ScientificArtifact.tsx` → `frontend2/src/components/reports/ScientificArtifact.tsx`
- [ ] `src/components/reports/ScientificParameters.tsx` → `frontend2/src/components/reports/ScientificParameters.tsx`
- [ ] `src/components/ui/StatusPill.tsx` → `frontend2/src/components/ui/StatusPill.tsx` — Primitiva aislada; migrar primero porque la usan 12 componentes.
- [ ] `src/auth.tsx` → `frontend2/src/auth.tsx`
- [ ] `src/components/ClinicalMetricsCards.tsx` → `frontend2/src/components/ClinicalMetricsCards.tsx`
- [ ] `src/components/ScientificResults.tsx` → `frontend2/src/components/ScientificResults.tsx`
- [ ] `src/components/cell-review/AuthenticatedCellImage.tsx` → `frontend2/src/components/cell-review/AuthenticatedCellImage.tsx`
- [ ] `src/components/cell-review/ScientificAnnotations.tsx` → `frontend2/src/components/cell-review/ScientificAnnotations.tsx`
- [ ] `src/components/cell-review/SmearCaseHeader.tsx` → `frontend2/src/components/cell-review/SmearCaseHeader.tsx`
- [ ] `src/components/deployments/ModelApprovalModal.tsx` → `frontend2/src/components/deployments/ModelApprovalModal.tsx`
- [ ] `src/components/deployments/ProductionActivationModal.tsx` → `frontend2/src/components/deployments/ProductionActivationModal.tsx`
- [ ] `src/components/deployments/ProductionStepIndicator.tsx` → `frontend2/src/components/deployments/ProductionStepIndicator.tsx`
- [ ] `src/components/deployments/TechnicalContractModal.tsx` → `frontend2/src/components/deployments/TechnicalContractModal.tsx`
- [ ] `src/components/model-architecture/ArchitectureChart.tsx` → `frontend2/src/components/model-architecture/ArchitectureChart.tsx`
- [ ] `src/components/model-architecture/TraceCharts.tsx` → `frontend2/src/components/model-architecture/TraceCharts.tsx`
- [ ] `src/components/model-training/TrainingScene.tsx` → `frontend2/src/components/model-training/TrainingScene.tsx` — Clases `mt-root` y `mt-halo` no están definidas en ningún CSS (estilo inerte). Reconstruir con utilities + keyframes del theme.
- [ ] `src/components/reports/AnalysisWorkspace.tsx` → `frontend2/src/components/reports/AnalysisWorkspace.tsx`
- [ ] `src/components/reports/DatasetIntegrity.tsx` → `frontend2/src/components/reports/DatasetIntegrity.tsx`
- [ ] `src/components/reports/Stage2PublicationPanel.tsx` → `frontend2/src/components/reports/Stage2PublicationPanel.tsx`
- [ ] `src/components/stage2/Stage2EnablementModal.tsx` → `frontend2/src/components/stage2/Stage2EnablementModal.tsx`
- [ ] `src/features/analisis-frotis-v2/components/StandaloneHtmlModal.tsx` → `frontend2/src/features/analisis-frotis-v2/components/StandaloneHtmlModal.tsx` — Bloqueado: incrusta HTML externo de `public/analisis-frotis-v2/`. Solo el overlay y el header del modal se migran; el HTML embebido se conserva como artefacto intacto.
- [ ] `src/pages/SmearUpload.tsx` → `frontend2/src/pages/SmearUpload.tsx`

### Onda 2 — Features (dependen de la onda 1) — 17 componente(s)



- [ ] `src/components/reports/AssessmentEvaluationCard.tsx` → `frontend2/src/components/reports/AssessmentEvaluationCard.tsx`
- [ ] `src/components/reports/AssessmentExplanationCard.tsx` → `frontend2/src/components/reports/AssessmentExplanationCard.tsx`
- [ ] `src/components/reports/AssessmentExplanationDetail.tsx` → `frontend2/src/components/reports/AssessmentExplanationDetail.tsx`
- [ ] `src/components/reports/AutoAnalysisBadge.tsx` → `frontend2/src/components/reports/AutoAnalysisBadge.tsx`
- [ ] `src/components/reports/LineageBadge.tsx` → `frontend2/src/components/reports/LineageBadge.tsx`
- [ ] `src/components/cell-review/CellGradCamPreview.tsx` → `frontend2/src/components/cell-review/CellGradCamPreview.tsx`
- [ ] `src/components/cell-review/CellImageViewer.tsx` → `frontend2/src/components/cell-review/CellImageViewer.tsx` — `className={`cell-box ${visual.className}${isSelected ? ' is-selected' : ''}`}`: `visual.className` proviene de una función de clasificación. Decisión: que `classificationVisual()` devuelva un token (`--cell-ok`, `--cell-warn`) y aplicarlo con `bg-[var(--cell-ok)]` / `border-[var(--cell-ok)]`.
- [ ] `src/components/deployments/ActiveProductionModel.tsx` → `frontend2/src/components/deployments/ActiveProductionModel.tsx`
- [ ] `src/components/deployments/ActiveStage2Model.tsx` → `frontend2/src/components/deployments/ActiveStage2Model.tsx`
- [ ] `src/components/deployments/DeploymentReviewPanel.tsx` → `frontend2/src/components/deployments/DeploymentReviewPanel.tsx`
- [ ] `src/components/model-architecture/MathFunctionPanel.tsx` → `frontend2/src/components/model-architecture/MathFunctionPanel.tsx`
- [ ] `src/components/navigation/UserMenu.tsx` → `frontend2/src/components/navigation/UserMenu.tsx` — 1 estilo inline para el dropdown. Convertir a utilities y `--menu-height` si sigue siendo dinámico.
- [ ] `src/components/reports/ComparisonPython.tsx` → `frontend2/src/components/reports/ComparisonPython.tsx`
- [ ] `src/components/reports/LegacyArtifactMedia.tsx` → `frontend2/src/components/reports/LegacyArtifactMedia.tsx`
- [ ] `src/components/reports/UnlinkedRunsSection.tsx` → `frontend2/src/components/reports/UnlinkedRunsSection.tsx`
- [ ] `src/components/reports/XAIComparisonViewer.tsx` → `frontend2/src/components/reports/XAIComparisonViewer.tsx`
- [ ] `src/components/reports/XAIOverlayView.tsx` → `frontend2/src/components/reports/XAIOverlayView.tsx`

### Onda 3 — Layouts y composiciones — 37 componente(s)



- [ ] `src/components/model-architecture/ArchitecturePanel.tsx` → `frontend2/src/components/model-architecture/ArchitecturePanel.tsx`
- [ ] `src/components/reports/RunLineageChildCard.tsx` → `frontend2/src/components/reports/RunLineageChildCard.tsx`
- [ ] `src/components/reports/RunSummaryRow.tsx` → `frontend2/src/components/reports/RunSummaryRow.tsx`
- [ ] `src/components/cell-review/CellClassificationAuditModal.tsx` → `frontend2/src/components/cell-review/CellClassificationAuditModal.tsx`
- [ ] `src/components/cell-review/CellReviewWorkspace.tsx` → `frontend2/src/components/cell-review/CellReviewWorkspace.tsx` — 2.280 líneas y 87 clases; usa `[data-state=…]`, `[data-mobile-tab=…]` y `[aria-selected]`. Tailwind 4 soporta variantes de atributo: `data-[state=approved]:bg-green-100`, `aria-[selected=true]:…`. Migrar por secciones (header, paneles, tabla, modales).
- [ ] `src/components/cell-review/SmearAnalysisResultsView.tsx` → `frontend2/src/components/cell-review/SmearAnalysisResultsView.tsx`
- [ ] `src/components/explainability/CaseExplainabilityView.tsx` → `frontend2/src/components/explainability/CaseExplainabilityView.tsx`
- [ ] `src/components/model-architecture/ActivationTracePanel.tsx` → `frontend2/src/components/model-architecture/ActivationTracePanel.tsx` — 3 estilos inline y 45 utilities huérfanas; SVG con `stroke-dashoffset`. Convertir el trace en utilities y keyframes `--animate-trace`.
- [ ] `src/components/model-architecture/ArchitectureDetail.tsx` → `frontend2/src/components/model-architecture/ArchitectureDetail.tsx`
- [ ] `src/components/model-training/TrainingHistory.tsx` → `frontend2/src/components/model-training/TrainingHistory.tsx` — Heatmap dibujado en `<canvas>` con colores calculados en JS. Tailwind no interviene en la pintura: se migra el wrapper y se centralizan los colores del heatmap en el theme.
- [ ] `src/components/navigation/AppSidebar.tsx` → `frontend2/src/components/navigation/AppSidebar.tsx` — Colapso con `--sidebar-transition-duration` y `transform`. Mapear a `transition-[width,transform] duration-...` y mover la variable a `--sidebar-width` en el theme.
- [ ] `src/components/reports/AssessmentComparison.tsx` → `frontend2/src/components/reports/AssessmentComparison.tsx`
- [ ] `src/components/reports/AssessmentXAI.tsx` → `frontend2/src/components/reports/AssessmentXAI.tsx`
- [ ] `src/components/reports/ComparisonRunCard.tsx` → `frontend2/src/components/reports/ComparisonRunCard.tsx`
- [ ] `src/components/reports/ConsensusSamplesTable.tsx` → `frontend2/src/components/reports/ConsensusSamplesTable.tsx` — Bloqueado: material-react-table + `MRT_Localization_ES` + MUI ThemeProvider. Reescribir con `DataTable` (server-side pagination ya implementada en la capa de datos).
- [ ] `src/components/reports/GeneratedXAIComparison.tsx` → `frontend2/src/components/reports/GeneratedXAIComparison.tsx`
- [ ] `src/components/reports/RunSelectorDialog.tsx` → `frontend2/src/components/reports/RunSelectorDialog.tsx`
- [ ] `src/components/reports/ScientificPreflight.tsx` → `frontend2/src/components/reports/ScientificPreflight.tsx`
- [ ] `src/components/reports/ScientificReport.tsx` → `frontend2/src/components/reports/ScientificReport.tsx` — Combina material-react-table (bloqueado) + 4 gráficos recharts + 30 selectores `.trn-mrt .Mui*`. Migrar la página en dos passes: contenedores Tailwind primero, gráficos después (props), tabla al final con `DataTable`.
- [ ] `src/components/reports/ScientificRepresentations.tsx` → `frontend2/src/components/reports/ScientificRepresentations.tsx`
- [ ] `src/components/reports/TrainingExplanationAttempt.tsx` → `frontend2/src/components/reports/TrainingExplanationAttempt.tsx`
- [ ] `src/components/reports/TrainingRunGroupCard.tsx` → `frontend2/src/components/reports/TrainingRunGroupCard.tsx`
- [ ] `src/components/reports/TrainingRunsTable.tsx` → `frontend2/src/components/reports/TrainingRunsTable.tsx` — Bloqueado: misma dependencia. Reescribir con `DataTable` conservando la jerarquía run → grupo.
- [ ] `src/components/reports/TrainingXAIComparison.tsx` → `frontend2/src/components/reports/TrainingXAIComparison.tsx`
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

### Onda 4 — Páginas completas — 13 componente(s)



- [ ] `src/App.tsx` → `frontend2/src/App.tsx`
- [ ] `src/components/Layout.tsx` → `frontend2/src/components/Layout.tsx` — Shell de la app (app-shell, breadcrumb, datasource selector). Migrar tras sidebar y primitivas.
- [ ] `src/components/cell-review/SmearAnalysisImmersiveView.tsx` → `frontend2/src/components/cell-review/SmearAnalysisImmersiveView.tsx`
- [ ] `src/pages/AssessmentDetail.tsx` → `frontend2/src/pages/AssessmentDetail.tsx`
- [ ] `src/pages/CellReview.tsx` → `frontend2/src/pages/CellReview.tsx`
- [ ] `src/pages/Explainability.tsx` → `frontend2/src/pages/Explainability.tsx` — 481 líneas, 51 clases; comparte clases con `smear-analysis-immersive.css`. Reutilizar primitivas migradas (badges, chips, cards).
- [ ] `src/pages/ModelComparison.tsx` → `frontend2/src/pages/ModelComparison.tsx`
- [ ] `src/pages/ModelExplorer.tsx` → `frontend2/src/pages/ModelExplorer.tsx`
- [ ] `src/pages/ModelTraining.tsx` → `frontend2/src/pages/ModelTraining.tsx`
- [ ] `src/pages/RunDetail.tsx` → `frontend2/src/pages/RunDetail.tsx` — 1.180 líneas, 72 clases. Migrar en 4 bloques (header, métricas, artefactos, explicabilidad) para no romper el tracker.
- [ ] `src/pages/Runs.tsx` → `frontend2/src/pages/Runs.tsx`
- [ ] `src/pages/SmearAnalysisHistory.tsx` → `frontend2/src/pages/SmearAnalysisHistory.tsx`
- [ ] `src/pages/SmearWorkflow.tsx` → `frontend2/src/pages/SmearWorkflow.tsx` — 1.264 líneas con `[data-mode="setup"]` y `[data-mobile-tab]`. Mismo patrón: variantes `data-[…]`. Separar el scroll de actividad (`workflow-activity-scroll`, hoy sin definición CSS) con `overflow-y-auto`.

### Onda 5 — Módulo Frotis v2 (ya Tailwind): fusionar tokens y copiar — 18 componente(s)



- [ ] `src/features/analisis-frotis-v2/components/CellDetailModal.tsx` → `frontend2/src/features/analisis-frotis-v2/components/CellDetailModal.tsx`
- [ ] `src/features/analisis-frotis-v2/components/CellMicrograph.tsx` → `frontend2/src/features/analisis-frotis-v2/components/CellMicrograph.tsx`
- [ ] `src/features/analisis-frotis-v2/components/ImageAdjustmentsPopover.tsx` → `frontend2/src/features/analisis-frotis-v2/components/ImageAdjustmentsPopover.tsx`
- [ ] `src/features/analisis-frotis-v2/AnalisisFrotis2Page.tsx` → `frontend2/src/features/analisis-frotis-v2/AnalisisFrotis2Page.tsx`
- [ ] `src/features/analisis-frotis-v2/components/CellGallery.tsx` → `frontend2/src/features/analisis-frotis-v2/components/CellGallery.tsx`
- [ ] `src/features/analisis-frotis-v2/components/DifferentialSidebar.tsx` → `frontend2/src/features/analisis-frotis-v2/components/DifferentialSidebar.tsx`
- [ ] `src/features/analisis-frotis-v2/components/ExportModal.tsx` → `frontend2/src/features/analisis-frotis-v2/components/ExportModal.tsx`
- [ ] `src/features/analisis-frotis-v2/components/FullFieldView.tsx` → `frontend2/src/features/analisis-frotis-v2/components/FullFieldView.tsx`
- [ ] `src/features/analisis-frotis-v2/components/Header.tsx` → `frontend2/src/features/analisis-frotis-v2/components/Header.tsx`
- [ ] `src/features/analisis-frotis-v2/components/NotesDrawer.tsx` → `frontend2/src/features/analisis-frotis-v2/components/NotesDrawer.tsx`
- [ ] `src/features/analisis-frotis-v2/components/QualityView.tsx` → `frontend2/src/features/analisis-frotis-v2/components/QualityView.tsx`
- [ ] `src/features/analisis-frotis-v2/components/ReportView.tsx` → `frontend2/src/features/analisis-frotis-v2/components/ReportView.tsx`
- [ ] `src/features/analisis-frotis-v2/components/SlideViewer.tsx` → `frontend2/src/features/analisis-frotis-v2/components/SlideViewer.tsx` — 10 estilos inline dinámicos (zoom, translate, minimap, escala en µm). Decisión: conservar los valores como CSS variables (`--zoom`, `--tx`, `--ty`) y usar `transform-[scale(var(--zoom))]`; el tamaño del minimap sigue siendo dinámico por cálculo.
- [ ] `src/features/analisis-frotis-v2/pages/AnalysisAreaPage.tsx` → `frontend2/src/features/analisis-frotis-v2/pages/AnalysisAreaPage.tsx`
- [ ] `src/features/analisis-frotis-v2/pages/FullFieldReviewPage.tsx` → `frontend2/src/features/analisis-frotis-v2/pages/FullFieldReviewPage.tsx`
- [ ] `src/features/analisis-frotis-v2/pages/ReportPage.tsx` → `frontend2/src/features/analisis-frotis-v2/pages/ReportPage.tsx`
- [ ] `src/features/analisis-frotis-v2/pages/ReviewCellsPage.tsx` → `frontend2/src/features/analisis-frotis-v2/pages/ReviewCellsPage.tsx`
- [ ] `src/features/analisis-frotis-v2/pages/SpecimenQualityPage.tsx` → `frontend2/src/features/analisis-frotis-v2/pages/SpecimenQualityPage.tsx`

### Detalle de decisiones no triviales por componente

| Componente | Decisión de mapeo |
|---|---|
| **StatusBadge** | Clases `status` + `status-${normalized}` definidas en `styles.css`. Mapeo: objeto `STATUS_TONE = {ok:[...], warning:[...], error:[...]}` que devuelve utilities literales (Tailwind no permite nombres de clase dinámicos). |
| **StatusPill** | Primitiva aislada; migrar primero porque la usan 12 componentes. |
| **MetricCard** | Usa utilities huérfanas (`flex`, `text-xs`) que hoy no defina ningún CSS: se convierten en utilities reales de Tailwind, sin pérdida de comportamiento. |
| **ConfusionMatrix** | Tiene CSS propio (`ConfusionMatrix.css`, 173 líneas) y modificadores `--${result}${priority}`. Reproducir las 4 combinaciones como mapa de clases; el resto del layout con utilities. |
| **DataTable** | Base para reemplazar material-react-table: implementar paginación, sort y filtros como props, sin librería. |
| **AppSidebar** | Colapso con `--sidebar-transition-duration` y `transform`. Mapear a `transition-[width,transform] duration-...` y mover la variable a `--sidebar-width` en el theme. |
| **CellImageViewer** | `className={`cell-box ${visual.className}${isSelected ? ' is-selected' : ''}`}`: `visual.className` proviene de una función de clasificación. Decisión: que `classificationVisual()` devuelva un token (`--cell-ok`, `--cell-warn`) y aplicarlo con `bg-[var(--cell-ok)]` / `border-[var(--cell-ok)]`. |
| **CellReviewWorkspace** | 2.280 líneas y 87 clases; usa `[data-state=…]`, `[data-mobile-tab=…]` y `[aria-selected]`. Tailwind 4 soporta variantes de atributo: `data-[state=approved]:bg-green-100`, `aria-[selected=true]:…`. Migrar por secciones (header, paneles, tabla, modales). |
| **SmearWorkflow** | 1.264 líneas con `[data-mode="setup"]` y `[data-mobile-tab]`. Mismo patrón: variantes `data-[…]`. Separar el scroll de actividad (`workflow-activity-scroll`, hoy sin definición CSS) con `overflow-y-auto`. |
| **RunDetail** | 1.180 líneas, 72 clases. Migrar en 4 bloques (header, métricas, artefactos, explicabilidad) para no romper el tracker. |
| **Explainability** | 481 líneas, 51 clases; comparte clases con `smear-analysis-immersive.css`. Reutilizar primitivas migradas (badges, chips, cards). |
| **SlideViewer** | 10 estilos inline dinámicos (zoom, translate, minimap, escala en µm). Decisión: conservar los valores como CSS variables (`--zoom`, `--tx`, `--ty`) y usar `transform-[scale(var(--zoom))]`; el tamaño del minimap sigue siendo dinámico por cálculo. |
| **TrainingHistory** | Heatmap dibujado en `<canvas>` con colores calculados en JS. Tailwind no interviene en la pintura: se migra el wrapper y se centralizan los colores del heatmap en el theme. |
| **TrainingScene** | Clases `mt-root` y `mt-halo` no están definidas en ningún CSS (estilo inerte). Reconstruir con utilities + keyframes del theme. |
| **ActivationTracePanel** | 3 estilos inline y 45 utilities huérfanas; SVG con `stroke-dashoffset`. Convertir el trace en utilities y keyframes `--animate-trace`. |
| **ScientificReport** | Combina material-react-table (bloqueado) + 4 gráficos recharts + 30 selectores `.trn-mrt .Mui*`. Migrar la página en dos passes: contenedores Tailwind primero, gráficos después (props), tabla al final con `DataTable`. |
| **ConsensusSamplesTable** | Bloqueado: material-react-table + `MRT_Localization_ES` + MUI ThemeProvider. Reescribir con `DataTable` (server-side pagination ya implementada en la capa de datos). |
| **TrainingRunsTable** | Bloqueado: misma dependencia. Reescribir con `DataTable` conservando la jerarquía run → grupo. |
| **StandaloneHtmlModal** | Bloqueado: incrusta HTML externo de `public/analisis-frotis-v2/`. Solo el overlay y el header del modal se migran; el HTML embebido se conserva como artefacto intacto. |
| **Login** | Login de entrada: migrar pronto porque define el lenguaje visual del shell. |
| **Layout** | Shell de la app (app-shell, breadcrumb, datasource selector). Migrar tras sidebar y primitivas. |
| **CampaignConfiguration** | Grid `1fr 340px` con aside sticky; clases `field` y `campaign-saved` sin definición CSS. Mapear a `grid-cols-[1fr_340px]` + `sticky top-0` y breakpoints `lg:`. |
| **MiniConfusionMatrix** | Primitiva de reporte; reutilizar el patrón de `ConfusionMatrix` para evitar duplicar tonos. |
| **UserMenu** | 1 estilo inline para el dropdown. Convertir a utilities y `--menu-height` si sigue siendo dinámico. |

### Reglas de traducción aplicables a todos

| Situación en `frontend/` | En `frontend2/` |
|---|---|
| `:hover`, `:focus`, `:active`, `:disabled` | `hover:`, `focus:`, `active:`, `disabled:` |
| `@media (max-width: 1024px)` | `lg:` / `md:` según el umbral; revisar mapa de breakpoints |
| `style={{width: x}}` con valor calculado | `style={{'--w': x}}` + `w-[var(--w)]` |
| `[data-state="x"]` | `data-[state=x]:` |
| `!important` | eliminar; resolver con `@layer utilities` o reordenar clases |
| BEM (`block__elem--mod`) | utilities planas + un objeto de tonos |
| `--ds-*` en reglas | tokens del `@theme` (`bg-surface`, `rounded-card`, `shadow-card`) |

---

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
| Migrados | 18 |
| Pendientes | 100 |
| Bloqueados | 6 |
| % completado | 18/124 = 14.5% |
```

> **Matiz honesto:** los 18 marcados ✅ son los componentes del módulo `analisis-frotis-v2`, que ya usan Tailwind 4 y utilities; cuentan como migrados porque no requieren reescritura de estilos, pero **todavía no están copiados físicamente** a `frontend2/`. El contador de archivos realmente creados en `frontend2/` es 0: solo existe este mapa.

### Log

- **2026-11-10** — Inventario inicial completado: 124 componentes clasificados, 14 archivos CSS analizados (16.879 líneas), tokens extraídos y propuesta de `@theme`, 6 componentes bloqueados, orden de migración en 5 ondas derivado del grafo de dependencias. No se modificó nada en `frontend/`.
- _(pendiente)_ — Onda 0: andamiaje de `frontend2/` (package.json, vite, `styles.css` con `@theme`).
