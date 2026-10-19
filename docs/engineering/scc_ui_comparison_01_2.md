# SCC-UI-COMPARISON-01.2

Fecha: 2026-10-19. Implementación y pruebas automatizadas completadas; revisión visual autenticada pendiente.

## Alcance y referencias

Se modificó únicamente la presentación de la sección 01, su utilidad de proyección, estilos locales y pruebas. Se conservaron los cambios previos del árbol de trabajo, incluidos backend, documentación y HTML. No se modificaron PostgreSQL, contratos, selector, visor Python ni módulos científicos; no se ejecutaron procesos científicos ni operaciones Git de publicación.

Referencias revisadas: solicitud adjunta, análisis `Texto pegado(20261019-121916).txt`, `comparacion.html`, documentación de implementación previa `scc_ui_comparison_01.md`, auditoría SQL y contratos `scc_pre_1a.md` y `capstone_ui_css_policy.md`. No se localizaron por separado la propuesta anterior de redacción ni el prompt anterior: se utilizó la implementación y su documentación como equivalente disponible.

## Cambios

- `frontend/src/components/reports/ScientificPreflight.tsx`: elimina las expansiones que reproducían `EvidenceCell` por participante. Valores simples y compuestos suficientemente descritos permanecen inline. Checkpoint, checksum y evaluación conservan identificadores completos y copia sin una segunda expansión de linaje.
- `ConsolidatedDetail` clasifica subcampos estructurados: compartidos una vez, distintos o parcialmente acreditados en una mini-tabla y ausencias agrupadas por motivo y participantes. A2 conserva la diferencia de `campaign_id` en una expansión de procedencia de la partición, sin cambiar su clasificación científica ni repetir `campaign_snapshot`.
- A6 reúne rol, propósito, umbral, población y definición de métricas en la síntesis de «Protocolo y regla de decisión». El detalle conserva `protocol`, `decision`, `metrics_definition`, hashes, identidad de evaluación/checkpoint e información de intento. Campos desconocidos y errores conservan sus estados; los tres subcampos metodológicos no se consideran acreditados por tener métricas históricas. Las condiciones originales siguen en el diagnóstico técnico. Conteos derivados de las filas resultantes.
- `frontend/src/utils/preflightPresentation.ts`: igualdad estructural tipada con identificadores semánticos (`AB`, `CD`, `AC`, etc.), exclusión de valores ausentes, proyección de A6 y apertura/foco del destino de evidencia. La identidad seleccionada completa los identificadores no presentes en los campos proyectados; no se inventan datos ni se añaden consultas.
- `frontend/src/styles/scc-comparison.css`: tonos blue/violet existentes vinculados a grupos reales; se conservan zebra, contraste textual, desplazamiento horizontal y foco.
- `EvidenceLinks` remite por RUN a referencias reales y abre todos los ancestros colapsados antes de enfocar y desplazar al destino. Cuando no hay referencia proyectada, lleva al bloque técnico del RUN y dimensión. No se usan índices fijos de evidencia.
- `AvailabilityMatrix` sustituye los ocho bloques por una tabla de estados del backend y disponibilidad individual. Participantes con alias una vez, advertencia principal, acceso a motivos completos, alcance y referencias. Disponibilidad individual y comparabilidad metodológica permanecen separadas.
- Las claves de expansión incorporan selección y respuesta; los detalles previos dejan de renderizarse al cambiar evaluación, checkpoint o RUN.
- Reutilizados: `ParameterValue`, `CompactValue`, `CopyText`, `scc-equal`, `scc-compact-id`, `scc-composite-value`, badges A1–A6 y el detalle técnico existente.

## Verificación ejecutada

- `npm test --prefix frontend`: **389 PASS**, cero fallos y cero omitidas. Incluye igualdad estructural, particiones arbitrarias, ausencia/error, dos/tres/cuatro RUN, A6, procedencia, invalidez de expansiones, matriz, destino de referencias real y apertura/foco de ancestros; conserva regresiones de copia, caché, curvas y otros módulos.
- `npm run build --prefix frontend`: **PASS** (TypeScript y Vite). Permanece la advertencia de bundle mayor que 500 kB.
- `git diff --check`: **PASS**.

No se realizó inspección visual autenticada ni navegación real en navegador: responsive, contraste y teclado conservan mecanismos existentes y pruebas de estructura/interacción, pero no se certifica su apariencia final. No se realizaron nuevas pruebas contra PostgreSQL ni verificación física de artefactos. No se fijaron conteos de la selección histórica ni porcentajes de reducción de markup.
