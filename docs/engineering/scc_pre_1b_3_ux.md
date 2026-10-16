# SCC-PRE.1B.3-UX — Presentación compacta de Comparación Científica

Fecha: 2026-10-16. Implementación frontend y verificación automatizada completadas. Revisión visual responsive y E2E autenticada pendientes.

## Alcance y archivos

- `frontend/src/pages/ModelComparison.tsx`: importa la hoja exclusiva de SCC.
- `frontend/src/styles/scc-comparison.css` (nuevo): contenedor, densidad, columnas adaptativas, matriz, estados y visor Python.
- `frontend/src/components/reports/ComparisonRunCard.tsx`: tarjetas compactas y UUID copiable bajo detalles.
- `frontend/src/components/reports/ScientificPreflight.tsx`: matriz A1–A6 por parámetro, resumen por análisis, agrupación exacta de advertencias y acceso al visor.
- `frontend/src/components/reports/ComparisonPython.tsx` (nuevo): proyección Python de evidencia pública A4, resaltado como texto React y control de copia reutilizable.
- `frontend/tests/scc-preflight.test.mjs` y `frontend/tests/scc-selection.test.mjs`: 13 pruebas adicionales de presentación y comportamiento.
- Este informe.

No se modificaron backend, PostgreSQL, contratos científicos, servicios HTTP, hooks de selección/caché, páginas clínicas ni CSS compartido. Sin commit ni push.

## Inspección inicial y cascada

Se revisaron la política CSS, SCC-PRE.1A, auditoría B.1, ingeniería B.2/B.3, estilos, componentes y contrato público de Preflight. `main.tsx` importa tokens, estilos globales y CSS clínico; `ModelComparison.tsx` ya importaba primitivas y componentes de reportes. No existía una hoja exclusiva de SCC ni dependencia de resaltado instalada. Los estilos SCC anteriores están en `report-components.css` y se conservan.

La hoja nueva se importa después de las hojas del reporte y todos sus selectores incluyen `.ds-report.scc-page`, con mayor especificidad que las reglas compartidas. El padre `.app-content` ya tiene `min-width: 0`; no se altera el shell. Los colores, superficies, radios, controles y foco reutilizan tokens `--ds-*`. No se redefinen tokens globales ni se agregan dependencias.

## P1–P8

| Prioridad | Implementación |
|---|---|
| P1 | Contenedor de 1440 px máximo, centrado, ancho 100%, border-box y min-width 0. |
| P2 | Título estable de 22 px, texto principal/tablas de 14 px, metadatos de 12 px; separación de 14 px y tarjetas con `--ds-space-4`. |
| P3 | Cuatro columnas con ancho suficiente; dos hasta 1050 px de contenedor y una hasta 550 px mediante container queries. Las tarjetas no tienen ancho máximo individual. |
| P4 | Cabecera RUN dinámica, parámetros agrupados A1–A6, valores de configuración y cobertura en filas, estados originales por alcance, cabecera sticky y scroll limitado a la tabla. |
| P5 | Resumen compacto de los ocho análisis sin dictamen global; detalle Preflight cerrado, motivos y trazabilidad expandibles. |
| P6 | Se conserva una columna principal: cuatro tarjetas y cuatro estados por fila aprovechan el ancho sin introducir un aside que reste espacio a la matriz. |
| P7 | Tipografía estable, sin crecimiento proporcional al viewport. No se incorpora clamp opcional. |
| P8 | Tokens locales SCC para decisiones de densidad; reutilización de espacio, color, fuente monoespaciada, estados, radios y foco del sistema existente. |

No se amplía a 1600 px: no hay evidencia visual que justifique aumentar el ancho de lectura. Controles móviles y summaries tienen mínimo de 44 px; foco visible y estados textuales acompañan los colores.

## Tarjetas, matriz y advertencias

Las tarjetas muestran alias local RUN A/B/C/D, modelo enlazado al reporte, arquitectura, optimizador, learning rate, estado y quitar. UUID completo y copia, semilla, épocas y duración quedan en detalles cerrados. La evaluación, intento y checkpoint siguen accesibles en la selección explícita y en el detalle Preflight; no se agregan consultas para duplicarlos en la tarjeta.

La matriz tiene `Parámetro | Estado o diferencia | RUN…`. A1/A2 muestran identidad de versión y partición; A3 expone las observaciones de cobertura disponibles; A4 muestra parámetros persistidos; A5 registro/linaje y checkpoint; A6 evaluación/intento. Identidades y evidencia extensa están en detalles, no en cabeceras. Ausencias no se sustituyen por cero. Los dictámenes se toman del backend, sin reevaluar A1–A6. Las diferencias de configuración se presentan a partir de los códigos `CONFIGURATION_DIFFERENCE_*` recibidos, sin comparar valores para derivar estados científicos.

Las advertencias del resumen se agrupan sólo cuando coinciden código, tipo, mensaje y condición; se cuentan participantes únicos y se conservan motivos, participantes y referencias originales. No se limita la lista a tres advertencias. Etiquetas como «Partición no acreditada» y «Comparable con advertencias» conservan los códigos originales en el detalle. Los motivos de evidencia faltante permanecen en A1–A6 aunque no estén clasificados como advertencias en el resumen backend.

## Ver modelo en Python

Acceso único en Preflight → A4. Selector por RUN, descriptor de arquitectura/optimizador, vistas Configuración y Reconstrucción, procedencia y copia exacta del texto visible. Resaltado ligero mediante segmentos React; no HTML interpolado, eval, ejecución, carga de `.keras` ni exportación `.py`.

Configuración usa exclusivamente campos públicos conocidos de A4, con valores escalares presentes; conserva cero y false, omite nulos y no incorpora defaults. Distintos registros de evidencia se mantienen en bloques separados para evitar sobreescrituras silenciosas. No se proyectan rutas de checkpoint ni campos ajenos a la lista explícita. No se inventan capas, constructores ni llamadas al optimizador.

El contrato actual no acredita por separado declaración y ejecución efectiva, estructura serializada ni integridad física del checkpoint. Por ello Reconstrucción informa los tres niveles: parámetros persistidos; constructor/arquitectura faltante; checkpoint íntegro y compatible no verificado. No afirma que el texto sea un modelo reconstruible o entrenado. Métricas de compilación y otras propiedades no expuestas por A4 no se inventan.

## Verificación

Ejecutado localmente el 2026-10-16:

- `cd frontend && npm test`: **368/368 PASS**, cero omitidas. Incluye las regresiones existentes de autorización, selección, navegación, caché, invalidación, reintentos, acordeones, carga diferida XAI y páginas clínicas.
- Las 13 pruebas nuevas cubren RUN A–D, UUID fuera del texto principal y disponible en detalles, columnas con 2/3/4 TRAIN, preservación de motivos/estados/códigos, agrupación estricta, selección Python por RUN, ausencia de defaults/rutas privadas, límites de reconstrucción, copia exacta, fallo de clipboard y escape de texto persistido.
- `cd frontend && npm run build`: **PASS**, TypeScript de ambos proyectos y Vite. Permanece el aviso de bundle JS superior a 500 kB.
- `cd frontend && npm run lint`: **no disponible**, el proyecto no define script `lint`. No se declara lint aprobado; el build sí ejecutó TypeScript.
- `git diff --check`: **PASS**.

No se ejecutó validación visual ni sesión autenticada. El intento de iniciar Brave headless local terminó con código 134, sin producir DOM ni capturas; no había herramienta de navegador conectada. Los anchos 390, 768, 1280, 1440, 1920 y 2560 px quedan pendientes de inspección real, junto con overflow, contraste computado, teclado, zoom y clipboard en el despliegue. Los breakpoints descritos son implementación CSS, no mediciones de navegador. No se declara fidelidad a Stitch.

Pendientes opcionales: validar si una pantalla operativa necesita máximo de 1600 px o aside; incorporar reconstrucción sólo cuando un contrato futuro aporte constructor y checkpoint verificados. No se amplía el alcance científico para resolver esas limitaciones.
