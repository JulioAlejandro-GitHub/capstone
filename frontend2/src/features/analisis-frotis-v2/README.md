# Análisis de frotis v2

**Sistema visual actualizado el 4 de noviembre de 2026:** consultar [DESIGN-SYSTEM.md](./DESIGN-SYSTEM.md) para el diagnóstico de Tailwind 4.3.3, tokens aislados, reglas, catálogo de valores y evidencia antes/después. La auditoría y validación del 2 de noviembre que siguen describen la integración inicial.

Integración estática del ZIP `ejemplo---digital-hematology-analysis-platform.zip`, realizada el 2 de noviembre de 2026. No se ejecutaron las instrucciones del README de AI Studio: no se incorporaron Gemini, claves, Express, dotenv, motion ni una segunda aplicación.

## Auditoría previa

Capstone tiene React 19, Router 7, TypeScript 5.8 y Vite 7, CSS propio y componentes MUI. No tiene Tailwind ni script de lint. `App.tsx` define las rutas dentro de `ProtectedRoute` y `Layout`; la sesión se restaura mediante `AuthProvider`. El menú se define en `navigationConfig.ts` y se dibuja mediante `AppSidebar`/`NavigationIcon`; se reutilizó el icono `microscope`.

El ZIP tiene React 19, Vite 8, TypeScript 7, Tailwind 4 y Lucide, además de dependencias sin uso en los componentes. Se inspeccionaron sus componentes, datos, utilidades, HTML, configuración y recursos. Las cinco pestañas originalmente comparten estado en App; FULL FIELD y ANALYSIS AREA reutilizan FullFieldView. Las células y el visor se dibujan principalmente en SVG. El PNG y ambos HTML se conservaron en recursos locales. Se corrigió `/public/assets/`, que no es una URL pública válida en Vite.

Única dependencia de aplicación añadida en la integración inicial: `lucide-react`, para preservar los iconos originales. No se cambiaron versiones de React, TypeScript ni Vite. Desde CAPSTONE-FRONTEND-DS-01, Tailwind CLI 4.3.3 y PostCSS se declaran como herramientas de desarrollo y el CSS generado se aísla bajo `.frotis-v2`, con propiedades internas `--frotis-v2-tw-*`. No hay reset global ni plugin Tailwind en Vite. `layout.css` adapta altura, header, popovers y desbordamientos al layout existente; `tokens_frotis_v2.css` centraliza los valores compartidos y `viewer.css` separa los overlays de la geometría. No hay fuentes remotas esenciales. El HTML demostrativo incluye CSS local; el HTML de referencia se saneó retirando scripts y enlaces a recursos ausentes/remotos.

## Arquitectura y árbol

```text
frontend/
├── package.json / package-lock.json                     [modificados: Lucide]
├── src/App.tsx                                          [modificado: ruta protegida]
├── src/router.ts                                        [modificado: ruta canónica]
├── src/components/navigation/navigationConfig.ts        [modificado: menú]
├── src/features/analisis-frotis-v2/                       [nuevo]
│   ├── AnalisisFrotis2Page.tsx                           entrada y composición
│   ├── routes.ts                                        rutas/pestañas
│   ├── README.md
│   ├── hooks/useFrotisDemo.ts                            estado temporal y acciones
│   ├── data/mockData.ts                                  datos originales
│   ├── types/visor.ts                                   contratos
│   ├── utils/hematology.ts                               cálculo y reclasificación
│   ├── styles/{module,layout}.css                        CSS generado/adaptaciones
│   ├── pages/
│   │   ├── FullFieldReviewPage.tsx
│   │   ├── SpecimenQualityPage.tsx
│   │   ├── AnalysisAreaPage.tsx
│   │   ├── ReviewCellsPage.tsx
│   │   └── ReportPage.tsx
│   └── components/
│       ├── Header.tsx
│       ├── DifferentialSidebar.tsx
│       ├── CellGallery.tsx
│       ├── CellMicrograph.tsx
│       ├── SlideViewer.tsx
│       ├── CellDetailModal.tsx
│       ├── FullFieldView.tsx
│       ├── QualityView.tsx
│       ├── ReportView.tsx
│       ├── NotesDrawer.tsx
│       ├── ExportModal.tsx
│       ├── StandaloneHtmlModal.tsx
│       └── ImageAdjustmentsPopover.tsx
├── public/analisis-frotis-v2/                             [nuevo]
│   ├── visor-standalone.html
│   └── assets/aistudio/
│       ├── visor_full_d875328e.png
│       └── visor_analisis_d923d6e9.html
├── scripts/generate-frotis-css.cjs                        [nuevo]
├── tests/frotis-v2.test.mjs                               [nuevo]
└── tests/browser/frotis-v2.cjs                            [nuevo]
```

Todos los componentes visuales del ZIP se reutilizaron; no se reescribió la maqueta. Las dos vistas de campo comparten FullFieldView con `isAnalysisArea` diferente. Los cinco componentes de página son independientes. La URL gobierna la pestaña; el estado local permanece en el padre mientras se navega. Los datos están separados de la presentación para una futura sustitución.

## Rutas

| Ruta | Vista/componente |
|---|---|
| `/frotis/analisis-2` | Redirige a `review-cells`, conservando query |
| `/frotis/analisis-2/full-field-review` | FULL FIELD REVIEW / FullFieldReviewPage |
| `/frotis/analisis-2/specimen-quality` | SPECIMEN QUALITY / SpecimenQualityPage |
| `/frotis/analisis-2/analysis-area` | ANALYSIS AREA / AnalysisAreaPage |
| `/frotis/analisis-2/review-cells` | REVIEW CELLS / ReviewCellsPage |
| `/frotis/analisis-2/report` | REPORT / ReportPage |

Se conserva `datasource` en la navegación; el módulo no lo utiliza para consultar datos. El menú dice **Análisis de frotis 2** y utiliza el icono existente, sin alterar los demás enlaces.

## Interacciones y límites

Funcionan selector de casos, estado, presets, brillo/contraste/saturación/gamma, disposiciones dividida/galería/visor, categorías/búsqueda, selección, detalle por doble clic, reclasificación, marcado, notas, zoom/pan, regla, grilla HPF, marcadores, minimapa, información de escaneo, mapa de densidad demostrativo, edición de informe, firma simulada, CSV y modal HTML. PDF ofrece una respuesta explícita de demostración; impresión utiliza el diálogo del navegador. Configuración de escaneo informa que no hay escáner conectado. Los errores de portapapeles ya no anuncian éxito.

No hay persistencia. Recargar conserva la ruta pero reinicia datos. Cambiar de caso reinicia células/selección/notas usando el conjunto original de muestra; no representa estudios independientes completos. Los campos del editor de informe se reinician al salir de esa vista. La firma solo actualiza el estado en memoria. El HTML descargable es la demostración original, sin los cambios de la sesión. El visor y las métricas son simulados; no ofrecen mediciones ni resultados clínicos reales. En pantallas estrechas se permite desplazamiento dentro del área de trabajo para mantener utilizables las columnas.

El módulo no importa el cliente API ni llama backend, PostgreSQL, inferencia, YOLO, Google o autenticación adicional. Solo lee el HTML estático local para copiarlo. El shell de Capstone mantiene sus llamadas existentes de sesión y catálogo, y su indicador global de backend; estas no forman parte de la maqueta.

## Validación

Ejecuciones del 2 de noviembre de 2026:

- `npm --prefix frontend run build`: aprobado, incluye TypeScript de aplicación y configuración. Vite avisa del tamaño del bundle, sin error de compilación.
- `npm --prefix frontend test`: 464 pruebas aprobadas, 0 fallos (461 existentes y 3 nuevas).
- Chrome headless con Playwright: aprobadas redirección, cinco pestañas, recarga en cada ruta, menú, cambio de caso/estado, presets, layouts, detalle, marcado, reclasificación, notas, CSV, modal HTML y recursos HTTP 200. Sin errores de ejecución ni llamadas API adicionales durante interacciones.
- Inspección visual de captura de Chrome: sidebar conservado, cabecera adaptable y galería/visor dentro del área disponible. Aislamiento mediante selectores CSS locales; no se afirma una comparación visual exhaustiva de todos los módulos previos.
- Lint: no disponible en package.json; no se declara ejecutado.
- La sesión fue simulada en el navegador de pruebas mediante interceptación de solicitudes. No se verificó un inicio de sesión contra un backend real.
- npm avisó de Node 25/npm 11 en la instalación, frente a Node 22/npm 10 declarados. Se conservaron los engines y las versiones de herramientas del proyecto.

Para repetir la prueba de navegador, iniciar `npm run dev` en frontend y ejecutar:

```sh
PLAYWRIGHT_MODULE=/ruta/temporal/node_modules/@playwright/test \
CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
node tests/browser/frotis-v2.cjs
```

Playwright se instaló en un directorio temporal para la validación, sin añadirlo al proyecto. Se puede omitir CHROME_PATH si Playwright tiene su navegador instalado. La captura se escribe en `/tmp/frotis-v2.png` (configurable con SCREENSHOT_PATH).

El script `scripts/generate-frotis-css.cjs` usa las dependencias locales fijadas en el lockfile y se ejecuta en `predev` y `prebuild`. Durante una sesión Vite, ejecutar `npm run styles:frotis` al introducir nuevas clases; los cambios de valores en `tokens_frotis_v2.css` reciben HMR directamente. El generador ya no reescribe el HTML independiente. Consultar [el sistema visual](./DESIGN-SYSTEM.md) para la validación actual de 467 pruebas, lint y comparación de 14 estados.

## Etapa dinámica futura

Definir una fuente de casos y células que sustituya mockData; acordar identidad de muestras, contratos, permisos, persistencia de notas/reclasificación, firma y exportación real, y conexión a resultados científicos. Antes de implementar servicios, añadir pruebas de contratos y del flujo clínico. También conviene ampliar cobertura responsive, accesibilidad y regresión visual con datos reales. Nada de ello está implementado en esta etapa.

La normalización de nomenclatura del 4 de noviembre de 2026 se documenta en [NAMING-REFACTOR.md](./NAMING-REFACTOR.md), incluidas las URLs HTML de compatibilidad y las atribuciones de la referencia original.
