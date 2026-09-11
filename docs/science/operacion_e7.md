# Operación del protocolo y comparador E7

Esta entrega implementa preparación, lectura verificadora y comparación. No ejecuta TRAIN, EVALUATE, EXPLAIN ni TEST, ni selecciona Producción. PostgreSQL sigue siendo la autoridad. No hay migración E7: se reutilizan `audit_events` y `assessment_final_locks` de E6.

## Protocolo y plan

La configuración canónica es `malaria_dl_local_project/configs/science/e7_v1.json`. Su documento es [protocolo_e7_v1.md](protocolo_e7_v1.md). La matriz de 72 filas está en [matriz_e7_v1.json](matriz_e7_v1.json): 36 originales y 36 sintéticas no disponibles, sin dataset acreditado ni resultados.

`configs/science/e7_campaign_plan.json` contiene una solicitud E4 y su protocolo explícito. `science.protocol.campaign_plan` exige que E2/E4 reconstruyan exactamente los 12 hashes congelados de E7; un cambio de defaults produce rechazo, no una nueva matriz silenciosa. El plan usa tres intentos máximos por miembro, con el primer intento verified. No se creó una campaña. Los conteos ficticios usados internamente para validar la forma del plan no son evidencia de un dataset; el congelamiento E4 real vuelve a exigir E1.

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m src.malaria_dl.science.cli check-protocol
```

Cambiar una decisión científica requiere una nueva versión y hash. No se modifica la historia de campañas ni las migraciones instaladas.

## Pruebas PostgreSQL sintéticas pendientes

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE7_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -s -p no:cacheprovider \
  tests/test_science_postgres.py
```

Son **3 casos**. Reutilizan el esquema sintético aleatorio de E4 y las migraciones aisladas de E5/E6. El caso de rollback hace visible únicamente el esquema de fixtures y luego mantiene las escrituras E7 en una transacción externa con savepoints. Comprueba un evento, igualdad de lectura, idempotencia, rechazo append-only, transacción utilizable y cero eventos desde otra conexión después del rollback. El fixture comprueba y elimina exclusivamente su esquema sintético según el mecanismo vigente. Los otros casos comprueban error de escritura sin exportación y el bloqueo final de una identidad E6 sintética, sin inferencia.

El caso de bloqueo sustituye deliberadamente la resolución de linaje por un fixture para aislar SQL; no acredita un candidato real. El análisis de selección y linaje se prueba aparte en `test_science_e7.py` y E6. Un rollback no acredita durabilidad de un commit entre sesiones ni tolerancia a caída física. No se aplican migraciones operativas.

## Comparación de referencias explícitas

Una referencia es el UUID de `assessment_attempts` de E6. E6 no creó un Run ID EVALUATE separado en `runs`: se conserva su identidad real, además de TRAIN Run ID, versión y checkpoint exacto. Nunca se busca la versión más reciente.

Después de disponer de experimentos autorizados, reemplazar `UUID_DATASET`, `UUID_CAMPAIGN` y `UUID_E6` por referencias verificables:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m src.malaria_dl.science.cli compare \
  --dataset-version-id UUID_DATASET --campaign-id UUID_CAMPAIGN --split val \
  --references '[{"evaluation_id":"UUID_E6"}]' \
  --export-dir /app/artifacts/science/e7-comparison
```

`--campaign-id` agrega el inventario completo de miembros/intentos, estados y exclusiones, verifica protocolo/snapshot/matriz y exige el primer intento TRAIN verified. Sin campaña, la selección sigue siendo la lista explícita persistida y no se atribuyen estados operativos ausentes. Las referencias que pertenecen a otras campañas se excluyen cuando se solicita una campaña.

`explanation_ids` es opcional por evaluación. Si se omite, se consultan **todos** los EXPLAIN verified vinculados al intento exacto, ordenados por UUID, y se verifican sus identidades y artefactos. Una lista explícita permite fijar el subconjunto; `[]` significa no incluir explicaciones. No hay selección por fecha. Las explicaciones no demuestran causalidad.

Toda lectura de E1 y del linaje se efectúa en transacciones READ ONLY mediante la vía `inspection=True`. No se llama al wrapper E1 que persiste auditoría dentro de esas lecturas. El reporte es una escritura posterior separada en `audit_events`, tipo `ml.scientific_comparison`, con UUID determinista derivado del hash, commit y lectura fresca. La exportación JSON/Markdown sólo procede de esa lectura: no funciona como fallback si PostgreSQL falla.

La CLI devuelve `report_id`, `report_hash` y estado. Con ambas clases exporta también curvas ROC/PR en PNG y SVG a partir de las coordenadas persistidas. Rechaza sobrescribir una carpeta que contenga un reporte diferente. Los resultados individuales son las predicciones inmutables de `assessment_results`; el reporte conserva su intento, identidad, conteo y SHA-256, y las métricas reconstruidas. Los agregados se separan por configuración, población y entorno. No se concatenan semillas. No se selecciona candidato con matriz original incompleta o población/entorno incompatibles.

Para registrar sólo faltantes con un dataset realmente verificado, usar `--references '[]'` y omitir `--campaign-id` si todavía no existe. Esto requiere PostgreSQL y no inventa métricas. El documento offline de preparación de esta entrega no equivale a ejecutar ese comando.

## Umbral y candidato antes de TEST

El checkpoint ya viene seleccionado por E5 con su política congelada. La propuesta de umbral E7 se calcula **sólo** a partir de scores VAL de ese checkpoint. No altera la decisión ni las predicciones de la evaluación fuente. `science.protocol.e6_protocol(protocol, threshold)` produce el protocolo E6 explícito para una futura evaluación autorizada con esa decisión. Si la evaluación no fue realizada con la regla/hash E7, queda como histórica exploratoria y fuera de la selección, aunque sus métricas sean válidas.

La matriz original completa permite seleccionar una configuración; el checkpoint representativo usa semilla 11 predefinida. El estado del objetivo y el carácter exploratorio de VAL permanecen visibles. La elección se congela al persistir el reporte. No se crea ni ejecuta un candidato durante esta entrega.

Para un uso futuro autorizado, la CLI ofrece `freeze-final --report-id UUID_REPORT --identity-file RUTA_IDENTIDAD_E6.json`. La identidad debe haber sido preparada mediante la inspección E6 para TEST; no es un archivo de resultados. El comando verifica el reporte, candidato, checkpoint, decisión, protocolo, snapshot, archivos sellados y opciones de inferencia, y registra la identidad exacta en `assessment_final_locks`. No hace inferencia. E6 exige ese bloqueo antes de reservar TEST. Esta capacidad no se ejecutó sobre datos operativos y no sustituye una autorización futura para TEST.

`--split test` en el comparador permite **leer resultados finales ya existentes**; no recalcula umbrales ni selecciona candidatos. Registra los IDs TEST consultados, pero no denomina intacto el conjunto: el historial previo no queda acreditado por ausencia de registros seleccionados.

## Límites científicos

- El dataset E1 designado anteriormente fue `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`. Esa designación no acredita de nuevo su acceso, integridad ni población para E7.
- VALIDATION compartida implica optimismo por selección. Una futura partición de calibración/comparación por paciente o estrategia anidada fuera de pliegue exige diseño prospectivo; no se altera el split aquí.
- La generación sintética no está disponible. No se sustituye por aumentación ni se rellena procedencia/proporción con suposiciones.
- IC por pacientes insuficientes o ausentes: valor ausente con motivo; nunca bootstrap independiente de células. Los intervalos mantienen checkpoint y umbral fijos; no incorporan toda la incertidumbre por selección adaptativa en VAL. Las desviaciones entre semillas son otra fuente de variación.
- No hay validación clínica, desempeño observado acreditado, ranking operativo ni campeón. Producción continúa manual. E8 no se inicia.
