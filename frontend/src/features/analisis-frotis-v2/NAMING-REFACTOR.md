# CAPSTONE-FRONTEND-VISOR-01 — Reporte de nomenclatura

Fecha: 4 de noviembre de 2026.

## Alcance y conteo

Se auditó el frontend completo: código, nombres de archivos, tipos, recursos, scripts, pruebas y documentación. Se excluyeron `node_modules`, `dist` y archivos de caché de TypeScript; los artefactos se regeneran con el build. El conteo corresponde a ocurrencias de texto, sin distinguir mayúsculas; los nombres de archivos se contabilizan aparte.

- **82 ocurrencias iniciales en 26 archivos.**
- **77 ocurrencias actualizadas**, incluyendo imports, comentarios, textos de interfaz, rutas de recursos y nombres de descarga.
- **4 archivos renombrados.**
- **5 ocurrencias originales conservadas**, justificadas abajo.
- Se añadieron **2 menciones de URLs antiguas** en la prueba de compatibilidad. Este reporte también conserva la denominación anterior para trazabilidad. Los dos archivos puente conservan nombres antiguos deliberadamente; su contenido ya utiliza Visor.

No se modificaron CSS, distribución, handlers de botones, lógica de estados, datos clínicos simulados, dependencias, backend ni PostgreSQL. Se conservaron el PNG original (mismos bytes), logo embebido y atribución de la captura de referencia. La identidad de la aplicación propia se denomina Visor, sin inventar una empresa llamada «Visor Labs».

## Archivos renombrados

| Antes | Después |
|---|---|
| `src/features/analisis-frotis-v2/types/visor.ts` | `src/features/analisis-frotis-v2/types/visor.ts` |
| `public/analisis-frotis-v2/visor-standalone.html` | `public/analisis-frotis-v2/visor-standalone.html` |
| `public/analisis-frotis-v2/assets/aistudio/scopio_full_d875328e.png` | `public/analisis-frotis-v2/assets/aistudio/visor_full_d875328e.png` |
| `public/analisis-frotis-v2/assets/aistudio/scopio_analisis_d923d6e9.html` | `public/analisis-frotis-v2/assets/aistudio/visor_analisis_d923d6e9.html` |

Tras renombrar los HTML, se añadieron archivos puente en sus ubicaciones antiguas. Son redirecciones locales mediante `location.replace`, con fallback de meta refresh y enlace. No duplican la aplicación ni el PNG.

## Rutas y enlaces

No se encontraron segmentos heredados en las rutas de React Router. No se creó una pestaña ni un segmento nuevo: `/frotis/analisis-2` y sus cinco rutas `full-field-review`, `specimen-quality`, `analysis-area`, `review-cells` y `report` permanecen iguales. El menú **Análisis de frotis 2** permanece igual.

| URL anterior | URL canónica actual | Compatibilidad |
|---|---|---|
| `/analisis-frotis-v2/visor-standalone.html` | `/analisis-frotis-v2/visor-standalone.html` | Redirección temporal; conserva query y hash |
| `/analisis-frotis-v2/assets/aistudio/scopio_analisis_d923d6e9.html` | `/analisis-frotis-v2/assets/aistudio/visor_analisis_d923d6e9.html` | Redirección temporal; conserva query y hash |
| `/analisis-frotis-v2/assets/aistudio/scopio_full_d875328e.png` | `/analisis-frotis-v2/assets/aistudio/visor_full_d875328e.png` | Referencias internas actualizadas; recurso, no ruta de navegación |
| `#/visor` en la captura HTML de referencia | `#/visor` | Enlace nominal de la referencia estática; no es una ruta React publicada |

El nombre de descarga CSV utiliza `visor_..._differential.csv`. El HTML se descarga como `visor-interactive-analysis.html`.

## Símbolos y componentes

El archivo de contratos exclusivamente local pasó a `types/visor.ts`; se actualizaron todos sus imports y el reexport de `CellItem` en hematology. Los tipos `ClinicalCase`, `CellItem`, `WorkflowTab`, `CaseStatus`, `ImageAdjustments` y los demás contratos no cambiaron de forma ni de nombre: ninguno incorporaba la denominación heredada. No había componentes, variables o funciones propios llamados `ScopioViewer`, `scopioViewer` ni equivalentes que requirieran renombrado.

Se actualizaron las referencias nominales en Header, CellDetailModal, CellGallery, CellMicrograph, DifferentialSidebar, ExportModal, FullFieldView, QualityView, ReportView, SlideViewer, StandaloneHtmlModal, ImageAdjustmentsPopover, entrada del módulo, hook, rutas, mockData y hematology. También se actualizaron el generador de CSS, README y las dos pruebas del módulo. Las clases CSS y los valores de estilo permanecen intactos.

## Referencias conservadas

| Ubicación | Ocurrencias originales | Justificación |
|---|---:|---|
| `src/pages/SmearUpload.tsx` | 1 | «Microscopio»: palabra española válida de otro módulo, coincidencia parcial |
| `tests/smear-workflow.test.mjs` | 1 | «microscopio»: descripción correcta de una prueba existente |
| `tests/smear-analysis-results-view.test.mjs` | 1 | Patrón negativo de regresión que evita introducir marcas heredadas en otro módulo |
| `public/analisis-frotis-v2/assets/aistudio/visor_analisis_d923d6e9.html` | 2 | Título «Scopio Labs» y alt «Scopio Logo» de la captura del proveedor; se conserva marca/atribución original y logo embebido |

Las referencias nuevas en `tests/browser/frotis-v2.cjs` son entradas antiguas de los dos casos de redirección. Las menciones de este reporte describen la auditoría y compatibilidad. No hay imports activos a `types/visor`, descargas canónicas antiguas ni referencias nominales heredadas injustificadas en la interfaz propia.

## Verificaciones ejecutadas

- `npm --prefix frontend run build`: aprobado; incluye las dos comprobaciones TypeScript. Advertencia existente de tamaño del bundle.
- `npm --prefix frontend test`: **464 aprobadas, 0 fallos**.
- `PLAYWRIGHT_MODULE=/tmp/capstone-frotis-css/node_modules/@playwright/test CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' node frontend/tests/browser/frotis-v2.cjs`: aprobado en Chrome headless. Verifica denominación Visor, menú, entrada/redirección, cinco pestañas con recarga, casos/estado, presets, disposiciones, detalle, marcado, reclasificación, notas, exportación CSV, modal HTML, recursos 200, firma simulada y guarda de autenticación. También verifica las dos URLs HTML antiguas, su redirección conservando query/hash y recarga en la URL canónica.
- Búsqueda final `rg -i visor frontend` excluyendo dependencias/build/cachés: solo los casos justificados arriba y este reporte.
- `git diff --check`: aprobado.
- Lint: el repositorio no tiene script ni configuración de lint; no se declara ejecutado.
- Sin nuevas llamadas API durante las interacciones verificadas. El único fetch propio sigue leyendo el HTML local, ahora bajo la nueva URL. El shell conserva las solicitudes preexistentes de sesión y catálogo.

El navegador usa una sesión simulada para probar la guarda existente. No se validó login contra un backend real. No se hicieron comparaciones de píxeles de todos los módulos; esta intervención no editó estilos ni distribución. No quedan problemas funcionales detectados. Los puentes HTML deben retirarse cuando ya no se necesiten enlaces anteriores.

## Detalle del inventario inicial

| Archivo | Ocurrencias |
|---|---:|
| `frontend/public/analisis-frotis-v2/assets/aistudio/scopio_analisis_d923d6e9.html` | 4 |
| `frontend/public/analisis-frotis-v2/visor-standalone.html` | 13 |
| `frontend/scripts/generate-frotis-css.cjs` | 1 |
| `frontend/src/features/analisis-frotis-v2/AnalisisFrotis2Page.tsx` | 2 |
| `frontend/src/features/analisis-frotis-v2/README.md` | 4 |
| `frontend/src/features/analisis-frotis-v2/components/CellDetailModal.tsx` | 2 |
| `frontend/src/features/analisis-frotis-v2/components/CellGallery.tsx` | 3 |
| `frontend/src/features/analisis-frotis-v2/components/CellMicrograph.tsx` | 2 |
| `frontend/src/features/analisis-frotis-v2/components/DifferentialSidebar.tsx` | 1 |
| `frontend/src/features/analisis-frotis-v2/components/ExportModal.tsx` | 2 |
| `frontend/src/features/analisis-frotis-v2/components/FullFieldView.tsx` | 1 |
| `frontend/src/features/analisis-frotis-v2/components/Header.tsx` | 6 |
| `frontend/src/features/analisis-frotis-v2/components/ImageAdjustmentsPopover.tsx` | 3 |
| `frontend/src/features/analisis-frotis-v2/components/QualityView.tsx` | 2 |
| `frontend/src/features/analisis-frotis-v2/components/ReportView.tsx` | 2 |
| `frontend/src/features/analisis-frotis-v2/components/SlideViewer.tsx` | 9 |
| `frontend/src/features/analisis-frotis-v2/components/StandaloneHtmlModal.tsx` | 6 |
| `frontend/src/features/analisis-frotis-v2/data/mockData.ts` | 5 |
| `frontend/src/features/analisis-frotis-v2/hooks/useFrotisDemo.ts` | 1 |
| `frontend/src/features/analisis-frotis-v2/routes.ts` | 1 |
| `frontend/src/features/analisis-frotis-v2/utils/hematology.ts` | 2 |
| `frontend/src/pages/SmearUpload.tsx` | 1 |
| `frontend/tests/browser/frotis-v2.cjs` | 3 |
| `frontend/tests/frotis-v2.test.mjs` | 4 |
| `frontend/tests/smear-analysis-results-view.test.mjs` | 1 |
| `frontend/tests/smear-workflow.test.mjs` | 1 |
