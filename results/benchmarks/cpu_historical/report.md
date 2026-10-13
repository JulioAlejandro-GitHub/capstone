# B1 — Reporte reproducible de resultados

Estado documental: `HISTORICAL_AUDIT` — evidencia histórica B1; no autoriza entrenamientos ni comparación causal CPU/GPU.

Snapshot: `2026-10-04T12:56:54.183938+00:00`. Base `malaria_experiments`; PostgreSQL 17.9 (Debian 17.9-1.pgdg13+1) on aarch64-unknown-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit. Resultado: **auditoría B1 completada con limitaciones explícitas de instrumentación; no certifica benchmark CPU puro ni comparación GPU**.

## Reproducción

Desde la raíz del repositorio, con PostgreSQL ya activo en Docker:

```sh
python3 scripts/benchmarks/b1_historical.py
```

Usa sólo la biblioteca estándar de Python y `docker compose exec -T db … psql`. No inicia servicios ni importa TensorFlow. Abre `BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY`, verifica `transaction_read_only=on` y termina con `ROLLBACK`. Las credenciales se resuelven dentro del contenedor; no se imprimen. El proceso escribe únicamente los entregables locales. Si cambia la evidencia, las aserciones detienen la generación ante cardinalidades o semántica inesperadas. `--snapshot /tmp/b1_snapshot.json` permite guardar temporalmente los resultados de SELECT y `--from-snapshot /tmp/b1_snapshot.json` regenerar desde esa captura (incluye identidades de muestras VAL; no se publica como entregable).


Código de extracción: [b1_historical.py](../../../scripts/benchmarks/b1_historical.py); catálogo: [b1_queries.py](../../../scripts/benchmarks/b1_queries.py); fórmulas y generación: [b1_report.py](../../../scripts/benchmarks/b1_report.py). SQL completo y explicación de JOIN: [SQL_B1.md](SQL_B1.md). Interpretación científica/técnica y tablas de métricas: [HALLAZGOS_B1.md](HALLAZGOS_B1.md).

## Entregables y procedencia

| Archivo | Filas | Fuente y contenido |
| --- | --- | --- |
| campaign_summary.csv | 1 | Q01/Q03/Q13–Q16 y agregados; dataset, protocolo, entorno, conteos e integridad |
| runs.csv | 12 | Q04/Q05/Q07/Q08/Q12/Q17; identidades, tiempos, configuración, métricas y validación |
| epochs.csv | 396 | Q06/Q11; métricas sin redondeo, índices de fase, eventos y diferencias temporales |
| artifacts.csv | 396 | Q09/Q10; artefactos por época, 12 seleccionados con artifact_id de catálogo |

Los CSV son UTF-8 con encabezado y JSON dentro de celdas estructuradas. Celda vacía representa ausencia, no cero; las estructuras JSON conservan null. Se preservan numeric de PostgreSQL con Decimal, sin convertir a float, y timestamps UTC con microsegundos. Los cocientes no terminantes usan precisión Decimal de 50 cifras; CSV conserva también sus componentes. Segundos para tiempo, bytes para tamaño/memoria, proporciones [0,1] para métricas. No se redondean los valores fuente para presentación en CSV.

## Identidad de los 12 RUNS

| Posición | Arquitectura | Optimizador | RUN UUID | Miembro UUID | Intento UUID |
| --- | --- | --- | --- | --- | --- |
| 0 | custom_cnn | adadelta | 565a1dac-9c51-411b-a76c-efeb1d38722c | c22c099b-408e-4e69-84cd-0c1583245950 | 01552c27-7257-4f62-ab53-cd01422f1247 |
| 1 | custom_cnn | adam | a1c310c5-1cb0-4b1e-afc4-b087ed13ab24 | 39557bc8-137e-4992-8418-680fe81163ac | 814694a7-19ea-424b-9a95-e83b257bc6d9 |
| 2 | custom_cnn | adamw | c96bb5c1-1edb-4ef3-9854-fd715c4025f4 | 5092d781-aa60-4f18-b0f6-4f5774e3984f | 3d2a5b5b-d4cf-42f8-9ddb-9c62f4259c30 |
| 3 | custom_cnn | sgd | cc925f74-3535-40e0-9060-23a06cea8024 | 4dfbad8d-8850-410f-8f18-c018188c1d67 | 8ba69e3f-0bb8-425a-a6cc-74582f1d2ff2 |
| 4 | densenet121 | adadelta | c6fc8261-375b-41bf-9c15-a1e6885184ef | 6d964447-7a8a-4e28-8550-bc1ba0b9236b | ac945acd-2426-4fe7-990f-e8470f8d411d |
| 5 | densenet121 | adam | 8cb547f3-8b32-4149-8992-66bcbf4f4543 | 411f6360-6a07-48e7-a11d-97ca9b242a08 | b80b7cde-efdd-43f6-aae3-4171e9f2e229 |
| 6 | densenet121 | adamw | 85870857-925b-4b9f-9533-a2855d254d77 | baffd0cb-6c64-4663-8c9e-05d73938f6a8 | de86a050-0713-4b40-a4b2-9fb394e4f4e7 |
| 7 | densenet121 | sgd | 3b914540-b13f-46d1-8047-38755ffd10f6 | d11adce6-e054-467f-be34-539f3cebb120 | b5d6d963-519c-48c3-9771-29c8ffcc7bf6 |
| 8 | vgg16 | adadelta | 6021d446-25d3-4347-8b28-20b02c5fccd2 | c11d8cd6-a98f-43bc-9018-0cceff415b15 | c287e3cd-ce08-46b6-baa4-0df6f5ad39e1 |
| 9 | vgg16 | adam | 1cc25957-2804-47fa-b84e-4888264147c3 | 26964f44-06e3-468b-a2ac-2790f8a3b2fd | 1f4c71a8-6a7e-45a1-a5b6-d9bdf20cb7fa |
| 10 | vgg16 | adamw | 9a8fc142-4e16-4e80-b0b9-8cede55c3ec9 | bb8af33e-0dc2-4f91-a8f3-071a56634b1c | 01a1c851-dd20-431c-82ce-f22e26ae7bb8 |
| 11 | vgg16 | sgd | 0bbdd732-1a7a-4360-8f05-5bb9f0d50773 | 144465f5-af08-4357-854c-391a375f7a2b | b06bcf1e-c38f-4994-86c2-6c304b7edd35 |

## Totales verificados

| Medida | Valor |
| --- | --- |
| sum_run_seconds | 138403.694 |
| run_span_seconds | 138446.265 |
| inter_run_gap_seconds | 42.572 |
| epochs | 396 |
| base_epochs | 263 |
| fine_tuning_epochs | 133 |
| phase_count | 20 |
| early_stopped_phase_count | 17 |
| clinical_objective_passes | 0 |
| epoch_artifact_count | 396 |
| selected_artifact_count | 12 |

Todas las selecciones de miembros se conservaron, sin exclusiones por métrica o duración. Los 12 RUNS tienen un intento aceptado y no se observan reintentos adicionales. Las consultas de métricas seleccionan sólo la evaluación final de VALIDATION; no ejecutan evaluación alguna.

## Comprobaciones ejecutadas

- 12 pares únicos = producto cartesiano 3×4, semilla 47, arquitectura/optimizador coincidentes entre configuración normalizada, campaña, snapshot de ejecución y runtime compilado.
- Claves e integridad Q14: `{"members":12,"runs":12,"unique_pairs":12,"invalid_accepted_attempts":0,"invalid_run_links":0,"missing_run_configurations":0,"missing_campaign_configurations":0,"missing_sessions":0,"unlinked_runs":0,"invalid_evaluation_links":0,"invalid_metric_links":0}`.
- Configuración RUN: SHA-256 válido, JSON canónico igual a resolved; configuración de campaña igual a ejecución salvo seed.
- 396 épocas globales y locales contiguas, cierres de 20 fases y completion coherentes; no se deduplicó ocultando conflictos.
- 12 duraciones positivas con diferencia exactamente cero entre campo duration y resta de timestamps; ningún solapamiento entre RUNS.
- 12 matrices de confusión reconstruidas, mismo conjunto de 2.693 identidades/etiquetas VAL, seis métricas recalculadas desde scores con tolerancia 1e-12 (máximo error 5.3632491064677406109093255710395155E-16).
- Artefacto seleccionado conciliado entre evaluación, catálogo, registro por época y completion por SHA-256, tamaño, versión, época y source_event_id.
- 2.044 eventos canónicos con secuencias contiguas y tiempos no decrecientes; intervalos derivados no negativos.
- Relectura de CSV: 12 RUNS, suma exacta 138403.693539 s y 396 épocas.

## Advertencias y alcance

Cinco valores `runs.completed_epochs=0` son inconsistentes; los otros siete coinciden. `training_history`, `run_metrics`, `run_checkpoint_policy`, `execution_logs` y `environment_packages` tienen cero filas para esta campaña. Los campos planos de entorno están vacíos, por lo que se conserva `execution_parameters.runtime_environment`. El entorno declarado difiere del registrado en ejecución. El flag `policy_satisfied` no implica objetivo clínico logrado. Se mantienen estas advertencias sin editar registros históricos.

No se verificaron archivos físicos ni se ejecutaron nuevas cargas de imágenes/modelos. `gpu_available=false` carece de telemetría de colocación: la aprobación documental de B1 no acredita ejecución exclusivamente CPU. Análisis descriptivo de una semilla y VAL reutilizada; no equivale a validación clínica o inferencia causal. La futura comparación Metal requiere la instrumentación detallada en HALLAZGOS_B1.

## Huellas de los CSV

SHA-256 del contenido exportado, para verificar que documentos y datos pertenecen a esta entrega:

| Archivo | SHA-256 |
| --- | --- |
| campaign_summary.csv | 708ccbd174fc49c628613f0858dc182cec02db251877f0eacf62c1f237081c95 |
| runs.csv | 3f9a4e6a0901bf710cf2b4a64bc1d1b1055e6e83d9d8af321eefc7dfce096560 |
| epochs.csv | b3adf697d2b2e5870ff8b287b8c2976b263c32b41e031c3eed8752b97cff650d |
| artifacts.csv | 476687106ec34ef2114a75f8ea64fd240fb7ab014017de63804cc81146c4a308 |
