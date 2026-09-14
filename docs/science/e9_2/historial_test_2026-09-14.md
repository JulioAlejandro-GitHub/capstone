# E9.2 — Historial de TEST, sólo metadatos

Snapshot READ ONLY, REPEATABLE READ: 2026-09-14 15:10:17.872640 UTC (12:10:17 America/Santiago). Consulta limitada a runs de tipo evaluation: IDs, estado, fechas, claves split/dataset_split/purpose/dataset_version_id/source_training_run_id. También se consultaron identidades E6 (sin samples, métricas o predicciones), IDs de locks finales y eventos de configuración ensemble; nombres de artefactos legacy, sin abrir sus archivos. No se consultó assessment_results ni contenido de predicciones, métricas o imágenes.

36 EVALUATE legacy completed, creados entre 2026-07-25 y 2026-08-19; 12 con dataset d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 y 24 sin UUID. Ninguno tiene split/dataset_split/purpose explícito en esas claves. Los nombres best_model_metrics.json, best_model_confusion_matrix.csv y best_model_predictions.csv no identifican por sí solos partición. Son nombres históricos leídos, no CSV generados por E9.2.

Cero assessment_identities E6, cero locks finales y cero eventos ml.ensemble_configuration al snapshot. Eso no prueba ausencia de actividad externa/no registrada. No se infiere el propósito histórico a partir de fecha o arquitectura.

La auditoría 0A documenta rutas legacy TRAIN con evaluación TEST final habilitada y EVALUATE/ensemble que podían volver a consumir TEST, incluso cuando el nombre de la orden no indicaba partición. Es evidencia histórica de capacidad/flujo de código, no prueba individual de que cada uno de los 36 runs haya consumido TEST ni de que los resultados se usaran para seleccionar. Las rutas actuales se han modificado: E5 prohíbe evaluate_best_on_test, E6 exige identidad/lock final y E8 sólo permite VAL. No proyectar el código actual sobre julio/agosto.

Clasificación:

- **Uso histórico confirmado por ejecución individual con partición explícita:** no establecido por las proyecciones inspeccionadas.
- **Uso para selección o ajuste confirmado:** no encontrado en este alcance; tampoco se acredita su ausencia.
- **No se encontraron registros:** sólo para identidades E6/locks/eventos de configuración y marcadores de partición en las claves consultadas; no para toda evaluación histórica.
- **Historial insuficiente para acreditar independencia:** sí. La ausencia de métricas consultadas por este agente no demuestra ausencia de exposición por otros usuarios.

Consecuencia: no llamar a TEST intacto ni evaluación confirmatoria independiente. E7 ya permite reporte final descriptivo con exposición registrada. La evaluación final podrá continuar en una subetapa autorizada después de congelamiento exacto y soporte técnico, bajo esta limitación, sin ajustes posteriores. Afirmaciones confirmatorias requerirían datos independientes cuya falta de exposición y selección esté acreditada prospectivamente; no basta renombrar/regenerar un split de datos observados. No se propone incorporarlos ni descargarlos aquí. Revisar metadatos/procedencia histórica adicionales si existen antes de E9.5, sin consultar rendimiento para tomar decisiones.
