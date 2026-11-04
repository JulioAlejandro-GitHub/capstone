# Evidencia CAPSTONE-FRONTEND-DS-01

Auditoría del **4 de noviembre de 2026**. Consultar el [diagnóstico, reglas y catálogo de 149 tokens](../../../frontend/src/features/analisis-frotis-v2/DESIGN-SYSTEM.md).

Los PNG `before/` se capturaron antes de modificar los estilos. Los PNG `after/` corresponden al resultado final. Las capturas proceden de Chrome headless, viewport 1600×1000, animaciones desactivadas, sesión/API simuladas. El commit inicial y las versiones de herramientas constan en [tool-versions.json](./tool-versions.json). No representan una prueba de autenticación ni datos reales.

Las 14 comparaciones obtienen 0 píxeles diferentes según Pixelmatch (umbral **0.1**, antialiasing excluido). La columna RGBA informa también la diferencia estricta de píxeles, sin ese filtro; por ello no se afirma igualdad binaria de todos los PNG. Los valores completos están en [comparison.json](./comparison.json), junto a 15 verificaciones de responsive y el resultado de tokens en vivo.

| Estado | Antes | Después | Diferencias Pixelmatch | Píxeles RGBA distintos |
|---|---|---|---:|---:|
| full-field-review | [PNG](./before/full-field-review.png) | [PNG](./after/full-field-review.png) | 0 | 0 |
| specimen-quality | [PNG](./before/specimen-quality.png) | [PNG](./after/specimen-quality.png) | 0 | 0 |
| analysis-area | [PNG](./before/analysis-area.png) | [PNG](./after/analysis-area.png) | 0 | 4 |
| review-cells | [PNG](./before/review-cells.png) | [PNG](./after/review-cells.png) | 0 | 62 |
| report | [PNG](./before/report.png) | [PNG](./after/report.png) | 0 | 0 |
| case-menu | [PNG](./before/case-menu.png) | [PNG](./after/case-menu.png) | 0 | 66 |
| image-popover | [PNG](./before/image-popover.png) | [PNG](./after/image-popover.png) | 0 | 1261 |
| cell-detail | [PNG](./before/cell-detail.png) | [PNG](./after/cell-detail.png) | 0 | 217 |
| notes | [PNG](./before/notes.png) | [PNG](./after/notes.png) | 0 | 384 |
| export | [PNG](./before/export.png) | [PNG](./after/export.png) | 0 | 3 |
| html-modal | [PNG](./before/html-modal.png) | [PNG](./after/html-modal.png) | 0 | 4 |
| history | [PNG](./before/history.png) | [PNG](./after/history.png) | 0 | 0 |
| workflow | [PNG](./before/workflow.png) | [PNG](./after/workflow.png) | 0 | 0 |
| model-summary | [PNG](./before/model-summary.png) | [PNG](./after/model-summary.png) | 0 | 0 |

Se conserva visualmente el shell y las páginas externas Historial, Analizar imagen y Resumen de Modelo IA en los estados capturados. No se afirma cobertura de todas las rutas existentes. La verificación responsive comprueba que el ancho del documento no excede el viewport, sin certificar cada interacción a ancho móvil.

Pruebas ejecutadas:

- [Build y TypeScript](./build.log): aprobados; aviso de bundle grande de Vite.
- [Tests existentes y de aislamiento](./tests.log): 467/467, cero fallos.
- [Lint del módulo](./lint.log): 24 archivos TS/TSX, cero errores; alcance y exclusiones explicados en el diagnóstico.
- [Navegación e interacciones](./browser.log): cinco pestañas/recarga, menús, presets, layouts, detalle/reclasificación, notas, exportaciones, recursos y guarda de autenticación.
- [Comparación visual y tokens en vivo](./design.log): aprobado; tokens de principal, mínimo del header, sidebar, radio y superficie; herencia en menú/modal y activación con Enter.
- [Árbol de dependencias](./dependencies.log): una sola versión de Tailwind, 4.3.3; PostCSS 8.5.15 compartido con Vite.

Para instalar exclusivamente las herramientas de auditoría en un directorio temporal:

```sh
npm install --prefix /tmp/capstone-frotis-css --no-audit --no-fund eslint@10.14.0 @eslint/js@10.0.1 typescript-eslint@8.72.1 @playwright/test@1.64.1 pngjs@7.0.0 pixelmatch@8.0.0
```

La generación de CSS usa las dependencias locales del frontend, sin depender de ese directorio temporal. Los comandos completos de validación, variables de entorno y configuración de Chrome están en [DESIGN-SYSTEM.md](../../../frontend/src/features/analisis-frotis-v2/DESIGN-SYSTEM.md). En esta sesión Vite se ejecutó en 5174 porque 5173 estaba ocupado. Para comparar esta línea base desde el script, usar este directorio como `DESIGN_EVIDENCE_DIR`; para una nueva línea base usar un directorio separado y ejecutar `capture` antes de editar. Mantener la versión de Chrome indicada en el JSON para interpretar diferencias.
