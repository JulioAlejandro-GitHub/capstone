# SCC-REPORT-SCI.1 — Reporte científico con evidencia persistida

Fecha de verificación: 2026-10-16. Implementación de consulta, sin cambios de esquema ni de datos experimentales.

## Resultado y decisiones

SCC incorpora curvas TRAIN/VAL, métricas clínicas, matrices de confusión y consenso/desacuerdos calculados en servidor. El Preflight permanece como resumen y matriz de evidencia; sus diagnósticos por análisis quedan en detalles técnicos. Las evaluaciones se navegan dentro del footer de cada tarjeta RUN. La evaluación inicial es la más reciente por fecha, con desempate determinista; esto es navegación, no una conclusión científica. Las siguientes consultas envían la identidad seleccionada explícitamente.

Esta política, solicitada en SCC-REPORT-SCI.1, amplía P2 de SCC-PRE.1A y reemplaza la prohibición de selección inicial del frontend B.3. El backend Preflight no elige evaluaciones por su cuenta. `evaluations` sin `source_assessment_attempt_id` conserva su identidad histórica; no se crea un intento ficticio.

Se leyeron la auditoría SQL obligatoria y los contratos/documentos PRE y CSS, y se comprobaron las columnas sobre PostgreSQL vigente. La inspección confirmó que `train_execution_records.kind` contiene las curvas y las predicciones VAL; `training_history` no es la fuente apropiada para esas ejecuciones. Los lectores previos restringían población a assessments y marcaban VAL histórica sin intento como insuficiente.

## Operaciones y responsabilidades

- Se amplía `ScientificReadRepository` con catálogo de evaluaciones, dataset/split/materialización, eventos por época, selección/checkpoint, métricas por `evaluation_id`, predicciones por época/fase/rol y referencias de representaciones.
- `AssessmentReadRepository` añade lectura completa por intento para cálculo exclusivamente en servidor; reutiliza la validación de pertenencia poblacional existente.
- `ScientificReportService` valida atribución y calcula consenso. `ScientificPreflightService` reconoce la fuente histórica, verifica su cobertura y mantiene dictámenes independientes. Preflight no calcula oracle ni consenso.
- Se reutiliza el router de comparación: `POST /models/comparison/report?datasource=malaria`. El POST transporta una consulta de lectura; no genera trabajos.
- Request Pydantic: `ScientificReportRequest`, derivado del contrato de selección PRE, con `module`, `offset >= 0`, `limit` 1–100 y categoría enumerada. Módulos: `catalog`, `curves`, `metrics`, `consensus`, `questions`, `representations`.
- Respuesta Pydantic: `ScientificReportResponse`, sobre JSON público validado, con `module`, `data`, `warnings`. El frontend tiene tipos específicos de los módulos. No se devuelven arrays completos de predicciones para cálculo cliente.
- La ruta exige los mismos permisos RUNS/MODELS/DATASETS/PREDICTIONS/ARTIFACTS que Preflight y rechaza principal local anónimo. Se conservan RBAC global, cliente HTTP y autenticación existentes.
- SQL parametrizado bajo READ ONLY + REPEATABLE READ y timeouts existentes. Fallos SQL del módulo producen 503 sanitizado; no una lista vacía. Preflight conserva savepoints y errores por dominio.
- Los valores públicos eliminan localizadores privados con `public_evidence`. Hash registrado y linaje no acreditan bytes actuales.

No se añadieron tablas, vistas, migraciones, guards de versión, escrituras científicas ni procesos TRAIN/EVALUATE/EXPLAIN/PCA/UMAP/CKA.

## Evidencia A1–A6

| Dimensión | Lectura actual |
|---|---|
| A1 | Versión, nombre, estado, estrategia, algoritmo, semilla y registros oficiales; UUID en detalle |
| A2 | Partición evaluada separada de conteos oficiales, controles de validación y snapshot de campaña |
| A3 | Materialización, reconciliación, versión coincidente; población VAL observada por `sample`, cobertura e intersección; consumo TRAIN individual informado separadamente |
| A4 | Configuración canónica; si no existe fila, snapshot persistido E2 de `runs.execution_parameters`; augmentación, optimizador/hiperparámetros, objetivo y políticas sin defaults actuales. Épocas ejecutadas contadas desde eventos, separadas del máximo configurado |
| A5 | Artefacto de checkpoint atribuido, TRAIN, época y fase coincidentes con selección; checksum registrado separado de disponibilidad e integridad física `not_checked` |
| A6 | Evaluación histórica final VAL, propósito, umbral, definición y métricas ligadas por `evaluation_id`; intentos independientes mantienen su propia identidad y verificación |

La tabla agrupa valores diferentes, evidencia que requiere advertencias o completar parámetros y valores iguales. Los grupos “Con diferencias” y “Comparables” comienzan abiertos; “Sin diferencias”, cerrado. El encabezado aclara que el grupo no sustituye un dictamen. Una expansión muestra todos los RUN de la fila. Los dictámenes originales y sus hallazgos permanecen en el diagnóstico técnico. El visor Python usa pestañas y serializa exclusivamente parámetros persistidos; no reconstruye capas no acreditadas.

## Curvas y métricas

Las curvas leen únicamente eventos `epoch`, conservan valores y definiciones, omiten series sin evidencia y rechazan ejes duplicados/ambiguos. Los huecos se representan sin valores y `connectNulls=false`: no se interpolan épocas ausentes. TRAIN y VAL se distinguen con trazos y etiquetas; cada serie puede desactivarse. Una referencia contextual permite mostrar un checkpoint a la vez. Se muestran épocas ejecutadas, máximo, final, seleccionada, política y métrica.

Se emplea Recharts (`ResponsiveContainer`, `LineChart`, `ReferenceLine`, barras, ejes, tooltip y leyenda), siguiendo la [referencia solicitada](https://recharts.github.io/en-US/examples/LineChartWithReferenceLines/). Las series adicionales llevan las claves originales y la definición persistida; AUC por época no se presenta como idéntica a ROC-AUC de evaluación final.

Las métricas históricas se relacionan por `evaluation_id` y se contrastan RUN de ejecución, umbral y checkpoint final. Los intentos independientes sin fila `evaluations` muestran solamente métricas de su verificación persistida; las ausentes siguen ausentes. Las tarjetas de valores destacados exigen evidencia común de split, dataset, población, definición, protocolo y umbral; los demás casos conservan resultados individuales y advertencia. No se reemplazan ausencias por cero.

## Consenso y complementariedad

Para VAL histórica se exige evento único `predictions`, `role=val`, época y fase del checkpoint seleccionado, semántica de score `probability_parasitized` y clase positiva 1. Nunca se toma el último evento de predicciones. Se validan identidad, duplicados, etiquetas, finitud/rango de scores, umbral y número de muestras; la matriz reconstruida debe coincidir exactamente con la persistida.

Para intentos independientes se utilizan resultados del intento exacto, su verificación y la pertenencia gobernada; la implementación admite decisión `>=`, clase positiva 1, scores raw y ausencia de calibrador. Otros protocolos quedan explícitamente sin análisis acreditado. No se alinean rutas relativas históricas con UUID `sample_id` sin una correspondencia probada. VAL y TEST no constituyen una población pareada única.

El backend alinea por clave, comprueba conflictos incluso fuera de la intersección completa y devuelve:

- CONSENSUS_TP/TN/FP/FN y desacuerdos: conteos sobre la intersección de todos los RUN.
- Matriz de acuerdo: igualdad de predicción entre dos RUN, numerador sobre N común.
- Solapamiento de errores: conteos donde ambos fallan, sobre la misma población.
- Errores y aciertos exclusivos: exactamente un RUN tiene ese resultado y los demás el contrario.
- Oracle: muestras con al menos un acierto / N común; no es un modelo desplegable.
- Alta confianza: error con score >= 0,9 si predice positivo o <= 0,1 si predice negativo. No acredita calibración.
- Baja confianza: distancia al umbral <= 0,05; indicador descriptivo, no incertidumbre calibrada.
- Cobertura: N común / población única del RUN. Faltantes respecto de la unión; exclusivas respecto de la intersección.

La tabla tiene filtro, orden determinista por muestra y páginas de 25. Una muestra histórica conserva su clave completa y copia; no se construye un enlace a imágenes usando equivalencias no acreditadas.

## XAI y representaciones

El módulo XAI consulta intentos persistidos compatibles por TRAIN, checkpoint y split; conserva método, muestra y contexto mediante `groupXAIComparisons` y el visor compartido `XAIComparisonViewer`. Las páginas e intentos se retienen en memoria. Se mantiene separado el flujo manual existente `TrainingAssessmentXAI`; abrir el reporte no genera explicaciones.

La inspección real encontró solamente `model_checkpoint` entre los tipos de artefactos actuales y ninguna tabla de embeddings/proyecciones/representaciones. El módulo de representaciones consulta referencias existentes; no genera datos. Si aparecen referencias futuras, se muestran como evidencia pendiente de atribución metodológica, no como proyecciones verificadas. No se implementó un nuevo lector de binarios de embeddings ni un contrato de resultados PCA/UMAP/CKA inexistente.

## Carga y caché

Cada módulo científico cerrado no consulta. Primera apertura: consulta; reaperturas: caché privada de promesas/respuestas. La identidad incluye datasource y selección exacta; errores se pueden reintentar. Curvas dependen del TRAIN, no del cambio de evaluación. Métricas, consenso y preguntas dependen de evaluación/intento/split/checkpoint. La actualización explícita cambia la revisión de evidencia. Usuario/permisos/datasource remonta el ámbito privado.

El catálogo pequeño se consulta al renderizar tarjetas porque es necesario para seleccionar la evaluación inicial. Preflight consulta el resumen; no devuelve series ni predicciones completas. Las preguntas consultan al abrir y comparten respuesta para la misma selección. Los procesos manuales XAI conservan sus controles existentes.

## Verificación independiente en PostgreSQL

A diferencia del documento SQL de referencia, los siguientes resultados se obtuvieron ejecutando el servicio nuevo contra PostgreSQL durante esta implementación. Las regresiones usan los identificadores auditados solamente en tests.

| Evidencia | Resultado observado |
|---|---|
| Dataset | Malaria Patient Split v1; FROZEN, patient_group, seed 42 |
| Splits | TRAIN 22.180 / VAL 2.693 / TEST 2.685 |
| Materialización | READY / PASS; versión coincidente |
| Épocas A/B/C/D | 26 / 16 / 14 / 31; total 87 |
| Selección A/B/C/D | 14 / 4 / 2 / 19 |
| Accuracy A/B/C/D | 0,954697 / 0,934645 / 0,949127 / 0,946899 |
| Matriz A (TN/FP/FN/TP) | 1340 / 28 / 94 / 1231 |
| Matriz B | 1326 / 42 / 134 / 1191 |
| Matriz C | 1311 / 57 / 80 / 1245 |
| Matriz D | 1336 / 32 / 111 / 1214 |
| Población común | 2.693; sin faltantes, duplicados o conflictos; cuatro matrices reconciliadas |
| Consenso TP/TN/FP/FN | 1169 / 1301 / 17 / 60 |
| Desacuerdos | 146 |
| Todos fallan | 77 |
| Oracle descriptivo | 2616 / 2693 = 97,140735 % |
| Errores exclusivos A/B/C/D | 10 / 27 / 13 / 8 |
| Aciertos exclusivos A/B/C/D | 14 / 5 / 11 / 6 |
| Alta confianza / cerca del umbral | 66 / 149 |

Preflight de A–D acredita curvas, métricas y consenso con sus advertencias de desarrollo, sin errores SQL. No se verificaron archivos `.keras` ni sus hashes físicos.

## Pruebas ejecutadas

```sh
docker compose exec -T backend pytest -q \
  tests/test_scientific_report.py tests/test_scientific_preflight.py \
  tests/test_scc_core.py tests/test_scc_art.py tests/test_scientific_results_v2.py
npm --prefix frontend test
npm --prefix frontend run build
ruff check backend_api/app/services/scientific_report.py \
  backend_api/app/schemas/scientific_report.py backend_api/app/routes/scientific_preflight.py \
  backend_api/tests/test_scientific_report.py
ruff check --select E9,F backend_api/app/repositories/assessments.py \
  backend_api/app/repositories/scientific_results.py backend_api/app/services/scientific_preflight.py
git diff --check
```

- Backend: **104 passed**. Incluye lectura operacional SELECT-only, reconstrucción, selección, duplicados, conflictos, scores/umbrales inválidos, intersección parcial, oracle, paginación, SQL fallido, identidades cruzadas, permisos y ausencia de imports de ejecución científica.
- Frontend: **374 passed**, sin omitidas. Incluye navegación inicial histórica, ausencia de paginación con una evaluación, identidad exacta, expansión de fila completa, pestañas, series y referencia, métricas/ausencias, consenso, diferimiento/caché y regresiones existentes.
- Build TypeScript y Vite: PASS con Node 22.23.1. Persiste advertencia de bundle >500 kB; no se declara optimización de empaquetado.
- Ruff y diff: PASS.

Chrome headless con Playwright temporal: respuestas científicas capturadas del servicio real de PostgreSQL; autenticación y transporte simulados e interceptados, sin envío de escrituras. Se comprobó apertura de curvas, métricas y consenso, nueve gráficos, ausencia de consultas de módulos cerrados, reapertura sin repetir consenso y ausencia de errores JavaScript. A 390 px, `document.scrollWidth = innerWidth = 390`. Capturas: [1440 px](../audits/scc_report_sci_1/desktop.png) y [390 px](../audits/scc_report_sci_1/mobile.png). Esta comprobación no es una sesión JWT real de usuario.

## Límites pendientes

- Validación E2E con credenciales reales, teclado/zoom/contraste y tamaños intermedios 700/1000/1340 px. No se declara ausencia universal de regresiones fuera de las suites ejecutadas.
- TEST independiente de A–D, consumo individual completo de TRAIN e integridad física actual de checkpoints no están acreditados.
- XAI visual con artefactos reales compatibles, y contratos/lectores de representaciones futuras, requieren datos adecuados; los cuatro RUN de referencia no los aportan.
- No se acreditan inferencias estadísticas, generalización clínica, calibración de probabilidades ni código de reconstrucción de capas ausentes.
- Se conserva el aviso existente de tamaño de bundle. La instalación de dependencias informó vulnerabilidades del árbol npm; no se aplicaron actualizaciones generales ajenas a SCC.

## Archivos modificados

Backend: `repositories/scientific_results.py`, `repositories/assessments.py`, `services/scientific_preflight.py`, nuevo `services/scientific_report.py`, nuevo `schemas/scientific_report.py`, `routes/scientific_preflight.py`, `tests/test_scientific_preflight.py` y nuevo `tests/test_scientific_report.py`.

Frontend: `pages/ModelComparison.tsx`, `components/reports/{ComparisonRunCard,ComparisonPython,ScientificPreflight}.tsx`, nuevo `components/reports/ScientificReport.tsx`, nuevo `types/scientificReport.ts`, `services/api.ts`, `styles/scc-comparison.css`, `tests/{scc-preflight,scc-selection}.test.mjs`, `package.json` y lockfile.

Documentación: este informe, índice `docs/README.md`, adenda del contrato PRE y capturas de auditoría. No commits, merges ni pushes.
