# SCC-UI-PREFLIGHT.2

Fecha: 2026-10-20. Implementación frontend validada con pruebas, build y renderizado local en Chrome del snapshot público real. No se modificaron backend, PostgreSQL, contratos, algoritmos A1–A6, elegibilidad ni capacidad del selector. Sin commit ni push.

## Cambios

- Resumen metodológico: participantes y referencias dinámicos, actualización funcional, advertencias A4 con valores proyectados por RUN. Se conserva el alcance de VALIDATION frente a TEST, incluidas evaluaciones independientes. Fecha y limitaciones físicas quedan en trazabilidad; se elimina el botón de navegación redundante y el título genérico de configuración incompleta.
- El acordeón presenta texto y color del estado agregado. Es una proyección visual de los veredictos existentes, con prioridad incompatibilidad, error técnico, evidencia insuficiente, advertencias y comparable. No modifica ningún veredicto ni habilita análisis. Error técnico usa tono neutro en el resumen; los diagnósticos individuales conservan su presentación existente.
- Se retiran identificación y badges A1–A6 redundantes de la cabecera, listas repetidas y enlaces de evidencia por fila. Los seis veredictos se conservan en su dimensión en el registro técnico; Dataset y Partición también muestran su estado en las tarjetas.
- A1/A2 usan seis tarjetas: Dataset, Partición, Distribución, Materialización, Integridad y Trazabilidad. `ConsolidatedDetail` comparte únicamente valores acreditados iguales y muestra diferencias o evidencia parcial por RUN. Integridad cuenta los estados registrados, sin asumir PASS para controles ausentes; el detalle completo permanece en un acordeón. Distribución usa los conteos persistidos y el total oficial, sin recomputar métricas. Se distingue partición gobernada, población evaluada y registro de consumo TRAIN.
- `CompactValue` conserva objetos, arrays, ceros, falsos, nulos y entradas vacías. Muestra seis entradas inicialmente y mantiene el resto accesible en un acordeón. UUID y hashes muestran prefijo/sufijo, nombre completo accesible y copia del original mediante icono; confirmación con `role=status` y original seleccionable si falla el portapapeles.

## Reutilización y archivos

- `frontend/src/components/reports/ScientificPreflight.tsx`: adapta `CompactValue`, `ConsolidatedDetail`, `EvidenceCell`, `VerdictBadge` y la matriz; incorpora `PartitionCards` y `MethodologicalWarnings` con las proyecciones existentes `projectField`/`classifyFields`. No añade consultas ni dependencias.
- `frontend/src/components/reports/ComparisonPython.tsx`: variante opcional `iconOnly` en `CopyText`, manteniendo sus consumidores de copia de código.
- `frontend/src/components/navigation/NavigationIcon.tsx`: añade el glifo de copia al componente existente sin modificar el catálogo de navegación.
- `frontend/src/styles.css`: retira exclusivamente las reglas globales de `scc-composite-value`.
- `frontend/src/styles/report-components.css`: incorpora su reemplazo acotado y tokenizado, grid adaptable, identificadores compactos y movimiento reducido.
- `frontend/tests/scc-preflight.test.mjs`: adapta las expectativas de la presentación retirada y agrega cobertura de valores, tarjetas, estados, ausencia de evidencia, copia y CSS.
- Este documento registra el cierre.

## Trazabilidad

En «01 — ¿Qué estamos comparando?» → «Detalle técnico y trazabilidad» → «Identificadores y fuentes A1–A6», organizada por RUN: checkpoint, checksum registrado, época/fase cuando el reporte las aporta, identidad e intento EVALUATE, valores de fuente, operación, referencia, fecha y verificación operacional. Se preservan también fuentes adicionales del snapshot. Los motivos originales conservan asociaciones a RUN y evidence_id en «Diagnóstico técnico por análisis».

Los fingerprints y la campaña tienen un detalle secundario en la tarjeta Trazabilidad. Las identidades EXPLAIN se conservan donde las aporta el reporte y en su módulo existente; no se inventan identidades que el preflight no proporciona. Registro operacional y checksum persistido no acreditan lectura física de bytes.

`internal_preprocessing` continúa como evidencia insuficiente en la tabla A4 y con su diagnóstico original en trazabilidad. No se interpreta ausencia como igualdad.

## Tokens

Se reutilizan `--ds-action-fg`, `--ds-fg-default`, `--ds-bg-hover`, `--ds-border-default`, `--ds-border-width`, `--ds-radius-sm`, `--ds-space-2/3/4`, `--ds-weight-medium`, `--ds-text-lg` y `--ds-status-neutral-fg/bg`. `scc-verdict` conserva las familias existentes `--ds-status-approved-*`, `--ds-status-warning-*`, `--ds-status-rejected-*` y `--ds-status-neutral-*`. Sin variables de color nuevas ni hexadecimales. Hover con borde de ancho estable, sin cursor interactivo falso; transición desactivada con `prefers-reduced-motion: reduce`. No se toca el análisis de frotis ni sus superficies.

## Verificación

- `cd frontend && npm test`: **407/407 PASS**, sin omitidas.
- `cd frontend && npm run build`: **PASS**, TypeScript y Vite. Persiste la advertencia del bundle de más de 500 kB; no se cambió el empaquetado.
- `docker exec capstone_backend python -m pytest tests/test_comparison_eligibility.py tests/test_scientific_preflight.py -q`: **74 PASS**. Incluye auditoría SELECT de los dos RUN y pruebas de preservación de elegibilidad y advertencia VAL.
- Snapshot público obtenido con `ScientificPreflightService.read` y selección de los intentos VAL verificados usados por la auditoría existente; renderizado con los componentes React modificados. Aserciones de presentación confirmaron semillas 11/47, épocas máximas 40/3, L2 0.001/0.0001, advertencia de umbrales e `internal_preprocessing`. Este snapshot tiene **15 referencias**; el conteo no se fija a las 18 de la imagen de referencia.
- Chrome headless sobre ese HTML/CSS real: ancho de documento igual al viewport en **1440, 700 y 390 px**; tarjetas en 4/2/1 columnas. Detalle de comprobaciones cerrado inicialmente; nombre accesible «Copiar identificador»; Enter abre el acordeón; movimiento reducido produce transición `0s`. Inspección de capturas de escritorio y ancho estrecho; se corrigió la altura excesiva inicial del bloque de comprobaciones.
- Pruebas de copia ejecutan el handler con portapapeles controlado, verifican el texto completo, confirmación y fallback. Pruebas React cubren 2/3/4/7 participantes, datos comunes/diferentes, listas, nulos, errores y conservación de trazabilidad.
- `git diff --check`: PASS.

### RUN auditados

| RUN | Elegible | VAL |
|---|---|---|
| `338136db-a207-47fc-bbf3-d17ce85c0dc2` | Sí | 2.693 muestras, umbral 0,4 |
| `bbbd5b60-afaa-4034-a504-a60ed642aafe` | Sí | 2.693 muestras, umbral 0,5 |

La población VAL coincide. A4 conserva evidencia insuficiente y A6 conserva `PROTOCOL_DIFFERENCE_DECISION`; las diferencias experimentales no se convierten en incompatibilidad. No se ejecutaron procesos científicos ni se escribieron datos experimentales.

## Límites

No estaban disponibles las tres capturas originales ni el documento «obs 01» mencionado: se utilizó la solicitud adjunta y el snapshot actual. La inspección de navegador se realizó sobre renderizado local de los componentes con datos reales, no sobre una sesión autenticada completa de la aplicación. No se verificó el portapapeles del sistema ni se hizo auditoría con lector de pantalla. La página Comparación Científica adopta la superficie workbench; no se añadió soporte nuevo de tema ni se aplicó `.ds-report` al análisis clínico de frotis.
