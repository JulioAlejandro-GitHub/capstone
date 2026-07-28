# ADR-020: clasificación celular con modelo productivo y resultado experimental

- Estado: Aceptado
- Fecha: 2026-07-28
- Alcance: Prompt 8, Etapa 2
- Relacionado: ADR-002, ADR-003, ADR-004, ADR-009, ADR-014, ADR-015 y
  ADR-019

Para el flujo concreto de Prompt 8, la decisión 8 sustituye la generación
automática prevista de forma general en ADR-014: prevalecen la acción manual,
unitaria y el retry explícito exigidos por este alcance.

## Contexto

Prompt 7 conserva detecciones y crops inmutables, pero todavía no existe una
ejecución especializada que aplique el clasificador publicado, congele su
contrato y separe el resultado automático de la revisión experta. La base
histórica también contiene una vista `cell_predictions` sobre predicciones
legacy, cuya semántica no satisface el linaje científico de Etapa 2.

## Decisión

1. La única selección implícita autorizada es el slot activo
   `stage2/default`, representado por `deployed_model_versions` y respaldado por
   una `stage2_model_publication` activa del mismo `model_version`.
2. Una publicación de catálogo, el último TRAIN o un checkpoint aislado no son
   fallback. Ante slot ausente, duplicado o inválido se bloquea la inferencia.
3. TRAIN y EVALUATE deben estar `completed`; checkpoint, tamaño y SHA-256 se
   comprueban dentro de roots locales permitidos, sin symlinks.
4. Preprocessing, firmas, mapping, positive label y threshold proceden del
   snapshot publicado. No existe fallback silencioso a `0.5`.
5. Cada ejecución congela el modelo y un manifiesto determinístico de
   detecciones incluidas y excluidas. Una ejecución equivalente activa o
   completada se reutiliza; un fallo sólo admite un run nuevo por retry manual.
6. La salida canónica es `0=uninfected`, `1=parasitized`; se guardan ambas
   probabilidades, threshold, margen de decisión y cercanía técnica al
   threshold.
7. Predicciones y resumen automático son inmutables. Las revisiones humanas son
   append-only y producen un resumen revisado derivado, nunca una reescritura.
8. Grad-CAM es manual y unitario. Reutiliza la matemática canónica, genera
   heatmap y overlay nuevos en storage local y un fallo no invalida la
   clasificación.
9. El agregado es un resultado experimental de cribado. No es diagnóstico ni
   estimación validada de parasitemia.
10. La ejecución permanece síncrona fuera del event loop, sin workers, nueva
    cola, polling ni retry automático.
11. El endpoint de agregado separa `automatic_summary`, persistido e inmutable,
    de `reviewed_summary`, calculado como proyección de lectura. El desglose
    automático por imagen tiene la forma canónica `{"images": [...]}`.
12. La API aplica allowlists a filtros/enums y nunca acepta una storage key del
    cliente para leer artefactos. PostgreSQL conserva metadata; heatmaps y
    overlays PNG viven create-only bajo storage local y se sirven por endpoints
    autenticados sin revelar su key.

## Consecuencias

La inferencia queda reproducible y auditable, aunque un entorno con una
publicación visible pero sin `stage2/default` permanecerá bloqueado. Renombrar la
vista legacy a `legacy_cell_predictions` permite crear la tabla científica
especializada; los escritores históricos continúan usando `predictions`.
Grad-CAM incrementa storage sólo por acción explícita.

La decisión se materializa en la cadena lineal `20260728_01`,
`20260728_02` y `20260728_03`; la última revisión fija el contrato final de
integridad del summary. En el precheck de Prompt 8 no existe el slot real, por
lo que la conducta observable prevista es `awaiting_productive_model`, no una
inferencia exitosa.

## Alternativas rechazadas

- elegir la publicación más reciente o el último TRAIN;
- usar `0.5` por ausencia de threshold;
- inferir labels por filename o invertir scores heurísticamente;
- modificar crops, originales, checkpoint o predicciones;
- almacenar PNG en PostgreSQL;
- generar explicaciones para todas las células;
- presentar la fracción de candidatos como parasitemia o diagnóstico.
