# Auditoría E3 — VGG16 y contratos de entrada

Fecha: 2026-09-11. Dictamen: **NO APROBADA**. Implementación y pruebas locales realizadas; integración PostgreSQL E3 **NO VERIFICADA** por acceso denegado al socket Docker. No se interpreta ese error como caída de PostgreSQL.

## Línea base y revisión

Rama `main`, HEAD `9250a33a6d4472b1b97e02e416ac47345c11c264`. Árbol limpio al iniciar E3. Se contrastaron los 25 archivos del manifiesto E2: coincidieron todos los SHA-256 antes de editar. No había cambios posteriores sin commit que preservar. Los cambios actuales pertenecen a E3; se conservan íntegros los informes E1/E2. No se crea commit.

Se leyeron contrato 0B v1.1, informes E1/aceptación y E2/aceptación, manifiesto E2 y registro/adaptadores/configuración efectivos. No se encontraron AGENTS.md aplicables en repositorio/ancestros. E2 sigue aprobada en su revisión y alcance propios; su resultado PostgreSQL aportado por el usuario no se atribuye a E3.

La revisión efectiva es HEAD más los archivos y hashes de [manifiesto E3](etapa_3_manifiesto_2026-09-11.json). Incluye archivos nuevos y modificados, guía e informe; excluye el propio manifiesto para evitar autorreferencia. Los constructores de arquitecturas, guardas E1, módulo de persistencia E2 y política de publicación no se modificaron.

## Corrección e inventario comprobado

VGG16 usaba `rescale_0_1` en la configuración E2. Ahora descriptor/default/auto de nuevos TRAIN resuelven a `vgg16_imagenet`; se rechaza rescale para nuevos TRAIN. El auto global histórico permanece rescale. El adaptador devuelve el contrato completo y valida el grafo al compilar. CLI ya propagaba configuración efectiva al trainer: se comprobó `args.preprocessing = resolved.model.preprocessing`.

| Recorrido | Decode/resize/dtype | Escala y transformación | Forma, etiquetas/salida |
| --- | --- | --- | --- |
| TRAIN físico | Keras decode RGB; bilinear H×W; float32 | RGB 0–255; VGG: aumentación existente antes de preprocess; custom/dense conservan su orden | NHWC batch configurable; 0 uninfected/1 parasitized; sigmoid parasitized |
| VALIDATION | mismo loader físico | sin aumentación; una transformación externa | misma firma del TRAIN |
| EVALUATE | mismo loader con tamaño/modo del checkpoint | sin aumentación; `collect_predictions` recibe tensor transformado | firma/grafo/mapping validados antes de predict |
| EXPLAIN | mismo loader con contrato persistido | scores sobre tensor modelo; visualización RGB [0,1]; callback vuelve al dominio declarado | salida parasitized; pruebas de funciones, no campaña de explicaciones |
| Backend células | bytes del crop ya verificado; decoder TF RGB; bilinear; float32 | función común `transform_bytes` | valida dimensiones productivas y grafo; batch en servicio |
| Inferencia trazable/CLI individual | decoder TF RGB; bilinear; float32 | contrato persistido; sin inferencia desde carpeta | forma/dtype/output validados; TTA/ensemble fuera de prueba |
| Masivos EVAL/EXPLAIN | versión exacta ya seleccionada por E1/E2 | dejan de enviar defaults de tamaño/preprocessing del inventario | consumidor hereda contrato de la versión |

Ubicación única de transformación externa: loader/preprocesador, no adaptador ni grafo. VGG convierte RGB a BGR y resta medias; no divide por 255. Custom divide una vez. Dense divide una vez y conserva Normalization interna ImageNet. Los constructores no cambiaron. El backend antes decodificaba mediante PIL; la nueva ejecución acepta únicamente el recorrido TF explícitamente acreditado. Un histórico parcial no se reinterpreta como si acreditara ese recorrido.

El contrato `malaria_input_v1` conserva requested/resolved separados en E2 y añade escala de origen, canal, decoder, resize, versiones/ubicaciones, normalización interna y significado clínico. El finalizador lo toma del snapshot E2 o metadata explícita completa; elimina reconstrucción por tamaño/modo por defecto. Checkpoints existentes no se reescriben. Los errores de contrato son identificables; no se vuelcan credenciales.

## Matriz contractual y evidencia

| Requisito / escenario | Prueba | Resultado y límite |
| --- | --- | --- |
| PRE-01 / S06 | `test_vgg_reference_independent_and_dark_input`, resolución VGG | referencia TensorFlow + BGR/medias independiente; detecta /255 previo/doble aplicación; imagen oscura no dispara heurística |
| MODEL-02–03 / PRE-01 | `test_vgg_four_optimizers_step_reload` × Adam, AdamW, SGD, Adadelta | matriz completa, build con weights=None; un paso base y uno fine tuning, finitos; backbone congelado/base y últimas 4 capas/FT; guardar/recargar con scores equivalentes |
| PRE-02 / otras arquitecturas | `test_other_architectures_unchanged` ×2 | tensor idéntico a raw/255; mismo grafo con entrada de referencia da misma predicción; Dense interno coincide con referencia ImageNet |
| PRE-02 / S07 | fixture `.keras` + contrato sintético acreditado rescale | bytes/hash de modelo y metadata intactos; nueva configuración VGG no cambia tensores/scores; no acredita histórico operativo D4 |
| PRE-02 / S22 entrada | contratos/overrides inválidos y `test_loaded_signature_and_double_normalization_rejected` | tamaño/canales/dtype/escala/resize/mapping/arquitectura incompatible bloqueados; Rescaling accidental bloqueado |
| PRE-02 / consumidores | `test_consumer_tensor_and_prediction_equivalence` ×2 | mismo PNG no cuadrado y checkpoint; loader común, collect_predictions EVAL, scores y callback EXPLAIN, backend real `_preprocess`/validación y servicio trazable; inputs y scores equivalentes |
| S07/S22 bloqueo | `test_consumer_main_blocks_before_load_or_predict` ×4 | mains EVAL/EXPLAIN rechazan contrato faltante/override incompatible antes de load/predict; E1 sustituido sólo por fixture aislado en estos casos |
| Aumentación | `test_vgg_augmentation_before_preprocessing_only_on_train` | doble determinista verifica RGB0–255 antes de transformación; sin aumentación en validación; parámetros científicos no cambiados |
| TRACE-01–02/04 | finalizador + regresión E2, persistencia fallida antes de fit | contrato completo necesario; snapshot E2 lo transporta; no fallback; la comprobación PostgreSQL nueva sigue pendiente |
| DATA-01–04 | regresión E1 | UUID obligatorio, integridad, herencia y rechazos antes de inferencia conservados |
| S22 evaluación ajena / linaje integral | fuera de E3 | cierre E6; no atribuir equivalencia de tensores al cierre de reutilización de evaluaciones/calibradores |

Tolerancias: tensors frente a referencia `atol=1e-5`, display→tensor `2e-5` por redondeo float32; custom/dense reescalados igualdad exacta; predicciones `atol=1e-6`, recarga VGG `rtol=1e-5, atol=1e-6`. Inferencia con `training=False`/predict, sin aumentación aleatoria. Fixture VGG histórico usa grafo mínimo sintético, no pesos operativos. Los cuatro optimizadores usan VGG16 real con `weights=None`, sin descarga: prueban integración, no eficacia transfer learning/ImageNet ni sensibilidad clínica. No se acredita recuperación de D-6.

## Ejecuciones y resultados reales

Entorno local: Python 3.12.13, TensorFlow 2.17.1, Keras 3.14.1, NumPy 1.26.4, SQLAlchemy 2.0.51 y psycopg 3.3.4; CPU (sin GPU soportada).

Desde `malaria_dl_local_project`:

```sh
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/e3-mpl \
XDG_CACHE_HOME=/private/tmp/e3-cache .venv/bin/python -B -m pytest \
-q -p no:cacheprovider --basetemp=/private/tmp/e3-final \
tests/test_input_contract_e3.py tests/test_input_contract_postgres.py \
tests/test_model_registry_e2.py tests/test_model_configuration_postgres.py \
tests/test_dataset_stage1.py tests/test_dataset_evidence_postgres.py \
tests/test_governed_dataset_contract.py tests/test_run_evaluate_all_trainings.py \
tests/test_run_explain_all_trainings.py tests/test_train_checkpoint_policy_args.py \
tests/test_max_epochs_config.py tests/test_train_integration.py \
tests/test_evaluation_finalization_integration.py tests/test_checkpoint_policy.py \
tests/test_early_stopping_policy.py tests/test_training_model_version_finalizer.py \
tests/test_model_version_resolver.py tests/test_densenet_model.py
```

Resultado: **157 passed, 5 skipped**, 30.49s. Cinco omisiones: E1 PostgreSQL (1), E2 PostgreSQL (1) y E3 PostgreSQL (3); no son aprobaciones. Warnings: deprecaciones protobuf/NumPy-Keras, sin fallos técnicos. Después se añadieron cuatro casos de bloqueo de mains, documentados abajo; al reproducir ahora el comando completo también se incluyen esos cuatro casos.

```sh
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/e3-mpl \
XDG_CACHE_HOME=/private/tmp/e3-cache .venv/bin/python -B -m pytest \
-q -p no:cacheprovider --basetemp=/private/tmp/e3-guards-final \
tests/test_input_contract_e3.py -k consumer_main_blocks

PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/e3-mpl \
XDG_CACHE_HOME=/private/tmp/e3-cache .venv/bin/python -B -m pytest \
-q -p no:cacheprovider --basetemp=/private/tmp/e3-errors \
tests/test_max_epochs_main_smoke.py -k 'failure or interrupt'
```

Los cuatro casos nuevos de bloqueo: **4 passed, 18 deselected**, 2.85s.

Los dos casos de fallo/interrupción: **2 passed, 2 deselected**, 2.69s. Los casos legacy de éxito que ejercitan escritores CSV no se ejecutaron. No se afirma que toda la suite del repositorio esté aprobada.

Desde `backend_api`:

```sh
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 \
../malaria_dl_local_project/.venv/bin/python -B -m pytest \
-q -p no:cacheprovider --basetemp=/private/tmp/e3-backend \
tests/test_cell_classification_services.py
```

Resultado **39 passed**, 12.20s. Configuración sintética de tests, sin conexión operacional. La primera invocación desde la raíz no encontró `app`; se corrigió cwd/PYTHONPATH, no dependencias ni servicios.

Durante el desarrollo: primera suite 44 aprobadas/4 fallidas (fixture Dense comparaba 3D contra salida 4D; finalizadores tenían contrato parcial); ajustados los fixtures, 22 aprobadas. Primera regresión 156 aprobadas/1 fallida/5 omitidas por expectativa antigua del comando EXPLAIN; se actualizó a herencia de contrato sin eliminar la comprobación. Los nuevos tests de bloqueo inicialmente referenciaban `module.tf` inexistente en EXPLAIN (import lazy); se corrigió el doble para interceptar TensorFlow real. Estas incidencias no se presentan como defectos operativos ni pruebas aprobadas de una revisión anterior.

## PostgreSQL: aislamiento revisado, ejecución pendiente

`test_input_contract_postgres.py` reutiliza el helper E2 ahora extraído como función que retorna snapshot; la prueba E2 conserva su wrapper sin retorno. Opt-in E3 habilita sólo ese archivo. UUID/payload sintéticos. Tabla TEMP `runs` con resolución de namespace comprobada, sin UPDATE de `public.runs`; outer transaction + savepoints que absorben los commits internos. Se exige igualdad exacta JSONB, rechazo con dataset sintético distinto, transacción aún utilizable y un registro antes de rollback. El finally hace rollback también ante fallo y verifica en conexión posterior READ ONLY ausencia del UUID en public y de la tabla temporal, preservando diagnósticos originales si falla limpieza. No desactiva triggers/constraints ni ejecuta DELETE/migraciones/seeds.

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE3_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_input_contract_postgres.py
```

Esperado: **3 passed**. Obtenido en esta sesión: `permission denied while trying to connect to the docker API` (socket local, salida sanitizada). No se alcanzó pytest/PostgreSQL. No se cambiaron permisos/servicios ni se instaló otra BD. La revisión del aislamiento no sustituye la evidencia de ejecución. El round-trip con rollback, una vez aprobado, tampoco acreditará durabilidad de commit entre sesiones, permisos/constraints íntegros de public.runs ni persistencia de épocas/predicciones de etapas posteriores.

## Preservación y cierre

Sólo código/configuración/pruebas de entrada y documentación E3 modificados. Dataset UUID designado en E1, split, imágenes originales, checkpoints históricos, publicaciones y selección manual de Producción Etapa 2 no fueron modificados. Fixtures y checkpoints sintéticos se escribieron en temporales. No se ejecutó entrenamiento operativo, campaña científica, evaluación/calibración operativa ni EXPLAIN generador de resultados. Inspección AST de los Python modificados, ruff de los tres módulos nuevos y `git diff --check`: sin errores. Cero CSV en temporales de las verificaciones; no nuevos escritores/fallback de resultados.

| Área | Estado |
| --- | --- |
| Implementación local | COMPLETADA |
| Pruebas técnicas y regresión local | APROBADAS en alcance descrito |
| Compatibilidad histórica | APROBADA para fixture explícito; histórico operativo D4 NO VERIFICADO |
| Persistencia PostgreSQL E3 | NO VERIFICADA; repetir comando autorizado y contrastar revisión |
| Linaje/identidad/reutilización integral de consumidores | pendiente E6 |
| Beneficio clínico, recuperación D-6 | no demostrado; requiere ejecuciones científicas posteriores autorizadas |
| Puerta E3 | **NO APROBADA** por persistencia crítica pendiente |

No se inicia E4. La guía explica modos y consumo histórico sin reconstrucción por suposición.
