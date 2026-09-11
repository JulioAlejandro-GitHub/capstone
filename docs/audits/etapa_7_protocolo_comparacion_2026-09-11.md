# E7 — Protocolo científico y comparación sistemática

Fecha: 2026-09-11. **Dictamen técnico: NO APROBADA, integración PostgreSQL E7 NO VERIFICADA.** Implementación y pruebas locales completadas; queda pendiente la ejecución de tres pruebas sintéticas en Compose. **Ejecución científica: PENDIENTE / NO EJECUTADA EN ESTA ETAPA.** No se declara desempeño clínico.

## Línea base y alcance de la evidencia

- HEAD efectivo inicial y final: `15f2c957a99306fd5f77d8c7cd5ce0d317bd63a1`, rama `main`. Árbol inicialmente limpio. E7 añade archivos sin commit; no modifica archivos preexistentes, datos ni migraciones.
- Leídos contrato 0B v1.1, cierres E5/E6, política Alembic/BD Docker-only y contratos E1–E6. No se encontró `AGENTS.md` aplicable.
- Verificación local del manifiesto final E6: **63/63 hashes coincidentes**, al inicio y al cierre. El manifiesto describe una revisión anteriormente sin commit; el HEAD actual contiene esa implementación sin cambios en sus archivos acreditados.
- E6: **17 passed in 2.31s**, migración `20260912_02` instalada mediante wrapper con backup/preflight/rollback, y `/ready` con database/migrations/storage ready son evidencia **aportada por el usuario y conservada en el cierre E6**. No se presentan como nuevas comprobaciones operativas del asistente.
- Lectura de revisión y ejecución de pruebas E7 en Compose bloqueadas por permiso del socket. Error sanitizado: `permission denied while trying to connect to the docker API`. No prueba caída de PostgreSQL. No se cambiaron permisos/servicios ni se usó otra instancia.
- El dataset designado anteriormente por el usuario fue `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`; E7 no lo vuelve a acreditar ni lo sustituye por otro. La preparación conserva dataset/split/población ausentes hasta lectura E1 válida.

## Diagnóstico inicial

| Área | Existente/reutilizable | Faltante y cambio E7 |
|---|---|---|
| Dataset/split por paciente | `data/governed_dataset.py`, `dataset_integrity.py`: snapshot, materialización, checks y archivos sellados; E6 `lineage.dataset_samples` | Reusar vía READ ONLY/inspection, exigir mismo snapshot/población; no regenerar split |
| Registro/configuración/preprocesamiento | `models/configuration.py`, `models/registry.py`, configs E2 y `data/input_contract.py` E3 | Congelar 12 configuraciones por hash, arquitectura/inicialización/augmentación, validar reconstrucción por E4 |
| TRAIN/checkpoint/early stopping | `execution/train.py`, `execution/artifacts.py`, `execution/repository.py`; registros estructurados E5 | Separar selección de checkpoint, propuesta de umbral y candidato; no repetir implementación TRAIN |
| Umbral/calibración | E5 registra scores VAL y umbral; E6 `contracts.threshold` verifica procedencia; no calibrador aprendido de probabilidades en E6 | Regla E7 estricta `> 0,98`, sin relabel de históricos. Probabilidades raw y ausencia de calibrador explícitas |
| EVALUATE/EXPLAIN | Identidades, intentos, resultados, artefactos y bloqueo TEST en `assessment/*` | Resolver referencia explícita; validar de nuevo E1/E5/E6; conservar EXPLAIN exactos, sin versiones recientes |
| Campañas/intentos | `campaigns/contracts.py`, `repository.py`: matriz congelada y estado por miembro/intento | Plan E4 compatible y conciliación opcional de campaña explícita, incluidos fallos/interrupciones/exclusiones |
| Sintéticos/aumentación | Aumentación TRAIN de la receta E2; no generador sintético conectado encontrado | Ablación original+sintético planificada no disponible, sin técnica/proporción/procedencia inventadas |
| Comparaciones existentes | Vistas/endpoints históricos de catálogo/dashboard; no comparador científico pareado E7 | Servicio/CLI específico, sin modificar semántica histórica ni crear interfaz |
| Métricas e incertidumbre | E6 conserva predicciones individuales y confusión/tasas básicas | Añadir AP/ROC, F1/F2, BA, soportes, prevalencia, ausencias explicadas, dispersión entre semillas e IC por paciente |
| Persistencia | `audit_events` append-only y `assessment_final_locks` E6 | Reusar tablas, UUID/casts independientes, lectura posterior e idempotencia. **Sin migración** |

## Protocolo y decisiones

Versión: `capstone_science_e7_v1`.
SHA-256 canónico: `7db076d71c2143934f0b3bae47ff253f18d3f65c5c3f8efb2634586acbadbdf2`.

El [documento canónico](../science/protocolo_e7_v1.md) se genera desde `configs/science/e7_v1.json`; una prueba exige igualdad textual y hash. El cargador rechaza cambios bajo la versión congelada. La [matriz](../science/matriz_e7_v1.json) tiene 36 miembros originales y 36 sintéticos planificados no disponibles. Tres semillas comunes: 11, 29, 47. Cuatro optimizadores realmente soportados: Adam, AdamW, SGD, Adadelta. Presupuesto por configuración: 50 épocas base; hasta 20 fine-tuning en transfer y cero en Custom CNN. No se ejecutó ese presupuesto.

La configuración específica de cada arquitectura se conserva; igual número de configuraciones no significa igual costo computacional. El plan E4 fija tres intentos máximos y primer verified, y reproduce los 12 hashes E7. Durante implementación se detectó que `min_specificity=None` no puede congelarse en E4: se fijó explícitamente 0, sin inventar un mínimo clínico. Esta decisión está en las configuraciones finales, nunca aplicada a campañas existentes.

Selección VAL: sensibilidad estricta > 0,98, luego especificidad, F2 y mayor umbral. La grilla incluye scores observados y 0/1. Con ambas clases y probabilidades válidas, el umbral 0 permite sensibilidad 1 de manera trivial; por ello baseline, especificidad y límites se muestran siempre. Objetivo puntual no equivale a utilidad o validación clínica. Sin ambas clases el umbral es no estimable. El fallback del candidato informa objetivo no alcanzado; nunca se declara éxito por fallback.

La selección de configuración exige las 36 repeticiones originales completas, mismos pacientes/muestras y entorno. No toma la mejor semilla: el checkpoint representativo es el de semilla 11. VAL se rotula exploratoria por su reutilización adaptativa. Una futura subdivisión por paciente o estrategia anidada fuera de pliegue requiere diseño prospectivo; no se cambia el split.

## Implementación entregada

Rutas ML relativas a `malaria_dl_local_project/`:

| Archivo creado | Propósito |
|---|---|
| `src/malaria_dl/science/__init__.py` | Paquete E7 |
| `science/protocol.py` dentro del paquete | Protocolo/hash, matriz, plan E4 exacto, puente explícito a protocolo E6 |
| `science/statistics.py` | Métricas nulas con razón, umbral estricto, curvas, SD entre semillas, bootstrap por paciente y contrastes pareados |
| `science/comparison.py` | Lectura verificadora E1/E5/E6, clasificación, exclusiones, inventario de campaña y candidato determinista |
| `science/repository.py` | Reportes append-only con round-trip; bloqueo final exacto E6 sin inferencia |
| `science/reporting.py` | JSON/Markdown y PNG/SVG desde reporte persistido; rechaza sobrescritura de otro reporte |
| `science/cli.py` | `check-protocol`, `compare`, `export`, `freeze-final`; errores sanitizados |
| `configs/science/e7_v1.json` | Decisiones y configuraciones canónicas congeladas |
| `configs/science/e7_campaign_plan.json` | Solicitud/protocolo E4, sólo preparación |
| `tests/test_science_e7.py` | 28 casos locales controlados |
| `tests/test_science_postgres.py` | 3 casos opt-in PostgreSQL sintético |

Se añaden además el protocolo, matriz, [operación](../science/operacion_e7.md), [reporte de preparación](../science/preparacion_e7_v1.md), esta auditoría y el manifiesto E7. No se crea un reporte científico operativo ni un ganador como sustituto del acceso a BD.

E6 identifica EVALUATE con `assessment_attempts.id`, no con un `runs.id` nuevo; el comparador conserva esa identidad real y el TRAIN Run ID, model version y checkpoint. Las predicciones permanecen en `assessment_results`; el reporte persiste métricas completas, referencias, conteos y hashes. Ausencia de configuración histórica se conserva como limitación exploratoria y bloquea su elegibilidad.

## Correspondencia requisito → prueba/evidencia

| Requisito | Verificación |
|---|---|
| Mapeo positivo, confusión y métricas | Conteos manuales, sensibilidad/especificidad/F1/F2/BA, ROC y AP; etiquetas inválidas rechazadas |
| Métricas indefinidas | Sin positivos, sin negativos, sin predicciones positivas: null con motivo; curvas no inventadas |
| Umbral estricto | Caso 49/50 = 0,98 rechazado como cumplimiento; selección determinista y rechazo de TEST |
| Objetivo no alcanzado | Candidato de fixture con sensibilidad 0,98 conserva bandera false y causa exploratoria |
| Semillas y selección | Matriz completa, semilla representativa fija, orden estable y rechazo de repeticiones ambiguas |
| Particiones/dataset/decisión | Exclusión de mezcla de snapshot/partición y procedencia desconocida; históricos distintos no se relabelan |
| Linaje y EXPLAIN | Revalidación E6, rechazo de checkpoint/modelo cruzado y EXPLAIN de otra evaluación; regresiones E6 incluyen versiones múltiples |
| Pacientes/IC | Bootstrap reproducible ante reordenamiento, pareado idéntico con diferencia cero, grupos insuficientes/ausentes explícitos |
| Variabilidad | SD muestral ddof=1 y semillas distintas; no concatena predicciones |
| Campaña | Inventario conserva 35 miembros fallidos en fixture parcial; rechaza intento distinto del primer verified |
| Reporte | Hash protocolo/identidad, métricas contra prueba E6, selección consistente y coordenadas/exportaciones sintéticas verificadas |
| Falla BD | Exportación no escribe si lectura falla; caso PostgreSQL de escritura fallida preparado, aún no ejecutado |
| Bloqueo TEST | Rechazo local sin candidato; caso SQL sintético exacto/no inferencia preparado, aún no ejecutado |

## Resultados reales de validación

Desde `malaria_dl_local_project`:

```sh
.venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/test_science_e7.py tests/test_science_postgres.py \
  tests/test_assessment_e6.py tests/test_campaigns_e4.py
```

**110 passed, 3 skipped, 7 warnings in 13.05s**. Incluye 28 casos E7 locales y regresiones E4/E6. Los tres skipped son únicamente opt-in PostgreSQL E7. No se suman resultados de ejecuciones intermedias. Las advertencias corresponden a dependencias protobuf/SHAP y estructura de inputs Keras en fixtures E6; no falló ninguna aserción.

```sh
ruff check malaria_dl_local_project/src/malaria_dl/science \
  malaria_dl_local_project/tests/test_science_e7.py \
  malaria_dl_local_project/tests/test_science_postgres.py
```

**All checks passed.** Formato Ruff aplicado sólo a archivos nuevos.

`python -B -m src.malaria_dl.science.cli check-protocol` devolvió versión/hash esperados y 12 configuraciones. Se verificó también igualdad del plan JSON almacenado con `campaign_plan(load_protocol())`. Los **63 hashes E6** siguen intactos y `git diff --name-only` no muestra modificaciones de archivos preexistentes.

Intento real de integración:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE7_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -s -p no:cacheprovider \
  tests/test_science_postgres.py
```

Resultado: denegación del socket Docker, exit 1, **pytest no se inició**. Integración E7 **NO VERIFICADA**, no fallida en una aserción PostgreSQL. Éste es el comando pendiente para la terminal del usuario.

## Aislamiento y persistencia: esperado frente a obtenido

| Evidencia | Esperado en PostgreSQL | Obtenido en esta sesión |
|---|---|---|
| Reporte sintético | Inserción y lectura idénticas, idempotencia: un evento | Implementado/revisado; NV por socket |
| Append-only | UPDATE rechazado, outer transaction utilizable | Implementado/revisado; NV |
| Fallo de escritura | Savepoint revierte, cero eventos parciales, sin fallback/export | Caso preparado; rechazo de fallback también probado localmente |
| Rollback | Cero eventos desde otra conexión, incluso al finalizar el cuerpo de prueba; esquema sintético eliminado | Fixture revisado, ejecución NV |
| Bloqueo final E6 | Identidad exacta permitida; otra identidad rechazada; cero predicciones | Caso sintético preparado, NV |

El caso de round-trip usa el mecanismo E4 para hacer visible **sólo el esquema sintético**, seguido de una transacción externa para reportes y savepoints para commits internos. El rollback E7 se comprueba desde otra conexión; el fixture E4 conserva su comprobación de ausencia/limpieza del esquema. Los otros casos permanecen bajo rollback del fixture. No hay DELETE de eventos ni desactivación de triggers/constraints. No se acredita durabilidad física ni commit operativo mediante estas pruebas aisladas.

Las lecturas verificadoras usan READ ONLY; la persistencia del reporte y del bloqueo futuro son transacciones separadas. El comando `freeze-final` no fue invocado sobre datos operativos. No se necesita ni se propone `make db-migrate` para E7.

## Pendientes separados

**Para cerrar técnicamente E7:** ejecutar los tres casos PostgreSQL anteriores en Compose, resolver cualquier fallo con evidencia sanitizada y actualizar auditoría/manifiesto. La falta de acceso no se sortea con otra BD o archivos de resultados.

**Para la ejecución científica posterior:** acreditar nuevamente E1 y población/exposición TEST; crear/congelar una campaña con el plan E7; autorizar/completar 36 entrenamientos y evaluaciones VAL explícitas; informar n/N y errores; decidir el tratamiento prospectivo del sesgo VAL; congelar candidato/checkpoint/decisión antes de cualquier TEST futuro autorizado. La ablación sintética permanece planificada hasta contar con generador TRAIN-only y procedencia/versionado. No se inicia E8.

No se ejecutaron entrenamientos completos, inferencia TEST operativa, calibraciones operativas, promociones ni modificaciones de datasets, split, imágenes, checkpoints existentes o publicaciones. La selección de Producción sigue manual.
