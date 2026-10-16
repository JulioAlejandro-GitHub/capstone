# SCC-PRE.1B.3 — Integración frontend del Preflight

Estado: implementación frontend y pruebas automatizadas aprobadas; validación visual y E2E autenticada pendiente.
Fecha: 2026-10-16.

## Alcance y correspondencia código → interfaz

La referencia `stitch_clinical_design_system.zip/screen.png` se inspeccionó como estructura visual. No se incorporaron HTML/CSS ni valores científicos de Stitch. Se conserva la selección TRAIN y la capacidad `catalog.comparison.scc_max_comparison_runs` de `ModelComparison`, sus `ComparisonRunCard`, la navegación y las clases `.ds-report`, `ds-accordion`, `report-section`, `report-evidence`, `report-table-scroll`, `report-data-table`, `ds-control` y `ds-button`.

Orden: selección TRAIN; controles opcionales de evaluación; resumen metodológico siempre visible; 01 detalle Preflight cerrado; 02 Historia de aprendizaje abierta; 03 resultados VAL/TEST cerrado; 04 evidencia/explicabilidad cerrada (XAI, representaciones, CKA, consenso y espacios futuros); 05 inspección de muestra cerrada. Los detalles nativos no comparten atributo `name`: sus aperturas son independientes. Historia anuncia SCC-TRAIN.1 y no consulta épocas ni dibuja curvas. Los espacios futuros no consultan ni calculan resultados.

V7 conserva su texto histórico con una precisión explícita de presentación, y la referencia prospectiva al final de B.2 se actualiza. No se cambian A1–A6 ni dictámenes del backend.

## HTTP, selección y contrato

`api.getComparisonPreflight` usa el cliente `request` compartido: `POST /models/comparison/preflight?datasource=…`, JSON y autenticación existentes. No hay `fetch` paralelo ni cambios SQL/backend. La consulta inicial requiere dos TRAIN y no exceder el máximo real; el backend también admite evidencia individual, pero esta pantalla espera una comparación configurada.

`types/scientificPreflight.ts` refleja `schemas/scientific_preflight.py`: selecciones solicitadas/efectivas, discriminantes de evaluación y observación, dimensiones, alcances, dictámenes, hallazgos, análisis, evidencia, poblaciones, checkpoints, errores y resumen. UUID/fechas se transportan como cadenas. No se implementan reglas científicas en TypeScript.

El control de selección reutiliza `getTrainingAssessments` paginado (100 por página) y `getAssessment` para recuperar la identidad del intento elegido, comprobando TRAIN, tipo e intento. No selecciona el primero ni el último. «Aplicar selección» envía `evaluation.source=assessment`, `identity_id` y `attempt_id`; split y UUID de checkpoint son opcionales explícitos. Sin ellos el backend atribuye lo que su evidencia permita. La selección enviada y la identidad/checkpoint del intento se muestran por separado.

El tipo admite también `source=evaluations` del contrato; el control visual ofrece los intentos E6 disponibles mediante el lector existente. No se agregó un catálogo de evaluaciones históricas ni consultas improvisadas a scientific-results para completarlo.

El resumen muestra participantes/arquitecturas procedentes exclusivamente de la respuesta, conteos por estado, mezcla de estados, advertencias, referencias y fecha. La tabla contiene A1–A6, estados y motivos por alcance, una columna por TRAIN, UUID completos, configuración pública, población/intersección/cobertura cuando existen, linaje y verificaciones no realizadas. No atribuye época/política/checksums ausentes. Cada análisis mantiene sus hallazgos, límites y disponibilidad individual, incluso frente a un fallo de otro análisis. HTTP/autorización y `ERROR_DE_CONSULTA` no se convierten en incompatibilidad científica.

## Retención, invalidación y XAI

La caché es memoria privada del árbol de comparación; no usa almacenamiento persistente ni cambia el `no-store` del endpoint. Retiene promesas idénticas y respuestas exitosas; elimina rechazos. Un rechazo viejo no elimina una entrada nueva después de actualizar. Los efectos descartan respuestas tardías y el render comprueba la identidad antes de mostrar datos.

Preflight: clave con datasource, selecciones completas (TRAIN/evaluación/intento/split/checkpoint) y revisión. Abrir/cerrar su detalle no consulta. Cambiar la selección efectiva cambia la clave inmediatamente. Cambiar usuario/permisos/estado de autenticación, datasource o conjunto TRAIN remonta el ámbito retenido. Logout desmonta la ruta protegida. No se comparte evidencia entre contextos de autorización.

XAI dejó de montarse en cada tarjeta. Se conserva `TrainingAssessmentXAI` y el visualizador/generador existente bajo aperturas explícitas. Los contextos y detalles se retienen por datasource/TRAIN/intento/revisión. El detalle mantiene el estado al cerrar; la visibilidad de los ancestros pausa sus consultas y el polling. La paginación no inicia páginas siguientes si ya se cerró XAI. Reabrir un resultado inactivo reutiliza lo retenido; un proceso ya iniciado puede reanudar seguimiento al abrir. No cambia la generación científica del backend ni se inicia generación automáticamente. La selección de contexto es explícita.

Cambiar parámetros de Preflight de un TRAIN invalida la instancia XAI de ese TRAIN, no las de los demás. Actualización explícita invalida la evidencia retenida; hay reintento local y actualización XAI. Una generación explícita notifica nueva evidencia al Preflight, también al observar su finalización, sin desmontar el resultado XAI. Las claves del visor conservan intento/muestra/clase y las identidades de modelo/checkpoint/dataset de sus componentes existentes.

No se promete frescura frente a escrituras externas de PostgreSQL: el resumen informa fecha y ofrece «Actualizar evidencia». No hay polling del Preflight ni biblioteca nueva.

## Archivos

Nuevos:

- `frontend/src/types/scientificPreflight.ts`: contrato TypeScript.
- `frontend/src/utils/comparisonCache.ts`: retención/deduplicación privada.
- `frontend/src/hooks/useComparisonEvidence.ts`: carga por identidad y descarte de respuestas antiguas.
- `frontend/src/components/reports/ScientificPreflight.tsx`: selección explícita, resumen, tabla y estructura de módulos.
- `frontend/tests/scc-preflight.test.mjs`: pruebas de B.3.
- Este informe.

Modificados:

- `frontend/src/pages/ModelComparison.tsx` y `components/reports/ComparisonRunCard.tsx`: composición y retiro del montaje inicial XAI.
- `frontend/src/services/api.ts`: operación POST tipada.
- `frontend/src/components/reports/AssessmentXAI.tsx`, `GeneratedXAIComparison.tsx` y `hooks/useExplainGeneration.ts`: carga diferida, retención, pausa del seguimiento y notificación de evidencia.
- `frontend/src/styles/report-components.css`: tabla ancha con encabezados fijos y UUID legibles, dentro de `.ds-report`.
- `frontend/tests/scc-selection.test.mjs`: aislamiento del nuevo módulo en las pruebas existentes de selección.
- `docs/audits/scc_pre_1b_1.md`, `docs/engineering/scc_pre_1b_2.md`, `docs/README.md`: precisión de presentación e índice.

## Verificación y límites

Entorno local: Node 22.23.1, npm 10.9.8. Sin dependencias nuevas.

- `cd frontend && npm test`: **355/355 PASS**, sin omitidas; 20 pruebas nuevas. Incluye regresiones de selección, navegación, XAI y páginas clínicas.
- `cd frontend && npm run build`: **PASS**, ambos proyectos TypeScript y Vite (149 módulos). Permanece el aviso de chunk JS mayor a 500 kB.
- `git diff --check`: **PASS**.
- No existe script frontend de lint; se ejecutó el chequeo TypeScript estricto del build. No se declara un lint no ejecutado.

Las pruebas nuevas ejecutan el cliente HTTP con transporte simulado, renderizado React en servidor y hooks/eventos mediante un arnés controlado: petición/autenticación, 2/3/7 columnas, A1–A6, estados parciales/no verificados, errores HTTP/403 y reintento, selección explícita, montaje/apertura/cierre, retención, invalidación, concurrencia y contextos de autorización. Son pruebas automatizadas de frontend; no sustituyen una sesión autenticada en navegador.

No hubo herramienta de navegador disponible: quedan pendientes inspección visual responsive/teclado/zoom, estilos computados y E2E contra backend real. No se certifica fidelidad visual completa respecto de Stitch. No se modificaron archivos clínicos, CSS de frotis, contratos científicos, backend, datos ni migraciones. No se ejecutaron procesos científicos, commit ni push.

SCC-TRAIN.1 podrá sustituir únicamente el contenido informativo de Historia de aprendizaje con su carga real y clave metodológica; B.3 no incorpora consultas de métricas por época ni gráficos.
