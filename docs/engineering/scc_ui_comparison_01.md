# SCC-UI-COMPARISON-01 — Sección 01

Fecha: 2026-10-19. Implementación y validación automatizada; revisión visual autenticada pendiente.

## Alcance

Se modifica exclusivamente la presentación de «01 — ¿Qué estamos comparando?» y la proyección pública que la alimenta. Se conservan selección, caché, visor Python, módulos científicos y dictámenes del backend. No se ejecutan procesos científicos, migraciones, commits ni consultas nuevas. Los archivos HTML de referencia no se modifican.

## Implementación

- `ScientificPreflight.tsx`: tres grupos con conteos derivados de parámetros y selecciones actuales. Con diferencias y Comparables abiertos; Sin diferencias cerrado. Diferencias conserva columnas por RUN y omite estado redundante. Sin diferencias muestra un valor y una igualdad A=B…; `tbody` por módulo y `rowSpan` incluye las filas de detalle abiertas. La expansión de un parámetro muestra simultáneamente todos los RUN.
- `preflightPresentation.ts`: igualdad tipada y estructural, claves de objetos ordenadas y arrays ordenados. Ausencia, objetos vacíos, objetos parcialmente nulos y errores de consulta no acreditan igualdad. Cero y falso son valores. Una evaluación histórica sin intento independiente conserva su null original; se compara su identidad existente. Fuentes contradictorias quedan como evidencia no resuelta, con sus referencias. Un error SQL conserva su estado.
- Coincidencias se calculan por valor, nunca por posición de RUN. Se usan tokens blue/violet/slate existentes, sin significado de aprobación o rechazo. CSS encapsulado en SCC y clases específicas de esta sección.
- Parámetros A4 se extraen de la proyección pública de configuración, incluidos los parámetros reales del optimizador. A5 usa selección de checkpoint y evidencia existente `comparison_checkpoint` para época, fase y checksum. A6 conserva evaluación, intento, rol, propósito y protocolo. No se rellenan campos ausentes con defaults.
- Las huellas A2 se leen de `campaign_snapshot`; materialización de `materialization_id`, según el repositorio real.
- Advertencias agrupadas por código, clase, mensaje y condición; diferencias de configuración agrupadas en una lista de parámetros. Se indican RUN afectados. El detalle técnico conserva motivo, condición, código, referencias y atribución individual; los análisis remiten a los motivos consolidados. Se mantienen las fuentes A1–A6 y sus valores completos.
- UUID y hashes usan resumen de ocho caracteres, expansión nativa al valor completo y `CopyText` existente. La ausencia común se consolida sin afirmar igualdad. Se distingue época seleccionada de ejecutada, checksum registrado de verificado y VALIDATION de TEST independiente.

## Proyección backend

No cambia el esquema `scc_pre_1`, endpoints, consultas SQL ni estados científicos. Se amplían dos objetos `EvidenceRef.value` antes reducidos a booleanos:

- `ScientificReadRepository.evaluation`: `evaluation_role`, `purpose`, `protocol_hash`, `metric_definition`, `split`, desde el registro ya leído.
- `ArtifactReadRepository.get`: identidad seleccionada y `checksum_registered`, desde el artefacto ya leído.

No se exponen rutas privadas. `availability` e `integrity` permanecen `not_checked`. La época/fase solo se muestra cuando la evidencia existente la proporciona; no se agrega una consulta para inventarla o deducirla.

## Validación

- `npm test --prefix frontend`: 382 pruebas PASS, sin omitidas. Incluye 2/3/4 RUN, reordenamiento, dos pares, tres iguales, todos diferentes, objetos, ausencia parcial/total, errores, expansión y cambio de evidencia.
- `npm run build --prefix frontend`: TypeScript y Vite PASS. Advertencia de bundle mayor a 500 kB.
- `docker compose exec -T backend python -m pytest tests/test_scientific_preflight.py tests/test_scientific_report.py -m 'not requires_docker_postgres' -q`: 64 PASS; 3 pruebas PostgreSQL excluidas explícitamente. Verifica checksum público sin atribuir integridad, rol/protocolo históricos e intento ausente, privacidad y regresión científica.
- `git diff --check`: PASS.

No se certifican conteos 16/1/51 de la selección de ejemplo: no son constantes ni un fixture productivo. No se ejecutó la comparación autenticada con esos RUN ni una auditoría visual de escritorio, móvil, contraste, tooltips y teclado. Las comprobaciones DOM y de interacción automatizada no sustituyen esa revisión. No se afirma validación física de artefactos ni integración nueva contra PostgreSQL.
