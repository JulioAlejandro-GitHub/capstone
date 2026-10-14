# CAPSTONE-DATA-01B.1 — Certificación de nuevos splits Single-cell

Estado documental: `HISTORICAL_AUDIT`. Fecha: 2026-10-14. **Dictamen: NO CERTIFICADO.**

Código inspeccionado: commit `1af4eeaf1ac65a11f30a99cd9edc2920d94f38ea`. Fuente de verdad: PostgreSQL operativo `malaria_experiments`, servicio Compose `db`. Las escrituras de prueba se ejecutaron exclusivamente en una instancia desechable PostgreSQL 17.9, con esquema exportado de la instancia actual y población sintética.

## 1. Respuesta ejecutiva

**NO. Ejecutar hoy el flujo público de `malaria_dataset_split_project` no crea automáticamente un segundo split científico con UUID nuevo y materialización independiente.**

Se acreditaron capacidades parciales, que no deben confundirse con el recorrido completo:

- El optimizador real admite otra seed. Con los mismos **201 pacientes y 27.558 registros actuales**, seeds 42 y 43 producen candidatos distintos y válidos: **70 pacientes cambian de partición**. La prueba fue exclusivamente en memoria, sin persistir asignaciones ni crear archivos de dataset.
- El esquema actual y las primitivas de repositorio permiten dos versiones con las mismas fuentes y asignaciones diferentes. Se demostró en PostgreSQL aislado con fixtures.
- `materialize_dataset_version` realmente escribe bajo el UUID del plan recibido. Dos planes sintéticos materializados por esa función producen carpetas y registros distintos, sin alterar la primera versión congelada en el fixture.
- **El flujo público no conecta esas capacidades para crear un segundo split:** el bootstrap genera siempre el UUID v1; la generación requiere una versión preexistente; la persistencia usa seed 42 y constantes aprobadas de v1; validación, construcción del plan y freeze rechazan otros digests. Los comandos de persistencia/materialización no aceptan un selector de versión.

No se modificó código funcional, no se creó ninguna versión en PostgreSQL operativo y no se implementó variabilidad de brillo, contraste o entropía. Se añadieron únicamente el informe, evidencia y pruebas de auditoría, infraestructura de pruebas aisladas e índice documental.

## 2. Evidencia y método

Artefactos reproducibles:

- [Pruebas nuevas de certificación](capstone_data_01b1_evidence/test_certification.py).
- [Makefile de auditoría](capstone_data_01b1_evidence/Makefile) y [Compose aislado](capstone_data_01b1_evidence/compose.yaml).
- [Log de integración aislada](capstone_data_01b1_evidence/isolated_tests.log).
- [Sonda de solo lectura](capstone_data_01b1_evidence/readonly_probe.py) y [resultados PostgreSQL/archivos](capstone_data_01b1_evidence/readonly_results.json).

Orden del trabajo: primero se ejecutaron 19 pruebas existentes y aisladas de identidad/optimización; después se exportó **solo el esquema** PostgreSQL vigente y se ejecutó la suite adicional en una instancia desechable. Se contrastaron datos operativos mediante dos lecturas con `REPEATABLE READ, READ ONLY`. No se ejecutaron los tests de integración antiguos que crean drafts dentro de una transacción de la base operativa, aun cuando prometen rollback.

El Compose de auditoría utiliza proyecto `capstone-data01b1-audit`, red propia, sin puertos publicados, sin volumen operativo ni credenciales operativas. El almacenamiento PostgreSQL es `tmpfs`; el código y tests se montan read-only; las imágenes PNG sintéticas y sus materializaciones quedan en temporales del contenedor de tests. Se restauró el esquema con `ON_ERROR_STOP=1`, sin desactivar triggers ni constraints. Al terminar, el Makefile eliminó contenedores/red del proyecto de auditoría.

El primer intento de integración no llegó a ejecutar tests por un montaje relativo incorrecto (`file or directory not found: /split/tests/unit/test_materialization.py`). Se corrigió **solo el harness**, se añadió `create_host_path: false` al bind del código y se repitió: 17 PASS. No fue un fallo del materializador. El motor advirtió que la imagen backend local es amd64 sobre host arm64; las pruebas finalizaron normalmente bajo esa ejecución. No se modificaron los Compose operativos.

### Comandos ejecutados

Desde la raíz del repositorio:

```sh
make test-canonical-nlm-regression SOURCE_PYTHON=malaria_dl_local_project/.venv/bin/python
```

Resultado: **19 passed in 0.34s**. Incluye `test_identity_resolver.py`, `test_patient_group_stratified_v1.py` y `test_patient_split_optimizer.py`.

Exportación de esquema, exclusivamente lectura:

```sh
docker compose exec -T db sh -c 'PGOPTIONS="-c default_transaction_read_only=on" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --schema-only --no-owner --no-acl' > /tmp/capstone_data01b1_schema.sql
make -f docs/audits/capstone_data_01b1_evidence/Makefile test
```

Resultado final: **17 passed in 3.65s**: tres pruebas preexistentes de reconciliación y catorce casos nuevos contando la parametrización de comandos. Exportación auditada: SHA-256 `15fc8a3fc59d90645dcd230f967e8848383531c5070d722cf20beabe0aa7ec62`. El dump contiene el esquema, no datos científicos; no se incorpora como una segunda definición canónica del esquema en el repositorio. Para repetir, exportar el esquema vigente y pasar su ruta como `SCHEMA=...` si difiere del default del Makefile.

Sonda operativa, ejecutada dos veces:

```sh
docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/app/malaria_dataset_split_project/src backend python - \
  < docs/audits/capstone_data_01b1_evidence/readonly_probe.py
```

Esta sonda no ejecuta la CLI científica: consulta metadatos, prueba el rechazo de `prepare_split_generation` sobre FROZEN, calcula candidatos en memoria y lee hashes de los archivos existentes. No llama persistencia, validación con escrituras ni materialización en producción.

**36 casos de pytest PASS no equivalen a CERTIFICADO:** varias pruebas confirman precisamente los bloqueos actuales. Además, ambas ejecuciones de la sonda de lectura finalizaron correctamente y sus resultados fueron idénticos.

## 3. Recorrido ejecutable y funciones verificadas

En esta sección las rutas `src/...` pertenecen a `malaria_dataset_split_project`.

| Paso | Archivo / función | Comportamiento actual |
|---|---|---|
| Población existente | `src/malaria_split/splitting/patient_profiles.py::load_patient_profiles` | Consulta `dataset_versions → dataset_version_sources(role=PRIMARY) → clinical_identities → dataset_source_records`; exige identidades y registros VERIFIED. Preserva IDs fuente/paciente y hashes. |
| Optimización | `src/malaria_split/splitting/optimizer.py::optimize_patient_split(profiles, seed)` | Optimizador puro, seed parametrizable, asignaciones por paciente y evaluación de restricciones. No crea versión ni escribe DB/archivos. |
| Identidad de versión | `src/malaria_split/persistence/bootstrap.py::apply_scientific_bootstrap`, línea 496 | `uuid5(ID_NAMESPACE, f"{VERSION_NAME}:{VERSION_SEMVER}")`, con nombre/semver constantes de v1. |
| Generación CLI | `src/malaria_split/cli.py::generate_patient_split_v1`, línea 314 | Solo permite `--dry-run`; requiere versión DRAFT existente y sin asignaciones; calcula 42 repetido y 43 como comparación. No registra nueva versión. |
| Preparación de persistencia | `src/malaria_split/persistence/split_generation.py::prepare_split_generation`, línea 90 | Default `V1_ID`; versión debe existir; optimiza con literal 42, exige digest aprobado y 27.558 registros. |
| Persistencia | `src/malaria_split/persistence/split_generation.py::persist_split_generation`, línea 232 | Usa el UUID recibido en `PreparedSplitGeneration`, pero exige conteos/distribuciones y digest de registros aprobados de v1. No inserta `dataset_versions`. |
| Validación | `src/malaria_split/persistence/formal_validation.py::prepare_formal_validation`, línea 54 | Default v1; exige digests de pacientes y registros v1 antes de evaluar/persistir checks. |
| Plan físico | `src/malaria_split/persistence/materialization.py::build_materialization_plan`, línea 95 | Recibe UUID, default v1; exige VALIDATED, digests v1, doce checks y 27.558 registros. Selecciona asignaciones del UUID recibido. |
| Identidad materialización y escritura | `src/malaria_split/persistence/materialization.py::materialize_dataset_version`, línea 193 | UUID5 de `version:attempt`; destino `versions_root / str(plan.dataset_version_id)`; copia, SHA, staging, promoción y registro READY/PASS. |
| Freeze | `src/malaria_split/governance/freeze.py::_freeze_materialized_cell_dataset_version` | Recalcula fingerprints y exige otra vez ambos digests v1; no permite congelar un split Cell distinto por esta ruta sin corrección. |

El recorrido operativo materializa antes de congelar. No es válido «resolver» los bloqueos cambiando v1 de FROZEN a DRAFT: eso contradice su inmutabilidad y los triggers actuales.

## 4. Prueba A — Identidad: NO CERTIFICADA para una nueva versión automática

Constantes de `persistence/bootstrap.py`:

```python
VERSION_NAME = "Malaria Patient Split v1"
VERSION_SEMVER = "1.0.0"
ID_NAMESPACE = UUID("0372652d-465e-501a-95e7-eaf836c74430")
version_id = uuid5(ID_NAMESPACE, f"{VERSION_NAME}:{VERSION_SEMVER}")
```

La prueba ejecutable recalcula la expresión y obtiene exactamente:

```text
d8c0cab5-09dd-597f-9de7-7ca01aee2ec2
```

Ese mismo valor es `split_generation.V1_ID`. La seed, el resultado del optimizador y las asignaciones **no participan** en esa fórmula. Repetir bootstrap no significa generar una nueva identidad científica: reconoce o entra en conflicto con v1 según el estado/rama de bootstrap; no produce otro UUID.

`DatasetVersionRepository.add_draft` requiere que el llamador entregue `values['id']`. Aunque `dataset_versions.id` tenga un default PostgreSQL `gen_random_uuid()`, esta función inserta el ID explícitamente; el flujo actual no usa ese default para abrir automáticamente otro split.

Resultados ejecutados:

- `test_A_bootstrap_uuid_is_fixed_and_generator_default_is_v1`: PASS; verifica fórmula y defaults de generación/plan.
- `test_A_generation_requires_existing_version`: PASS; un UUID inexistente provoca `NoResultFound`, sin INSERT automático.
- `test_A_public_write_commands_reject_version_selector`: cuatro PASS. Los comandos `persist-patient-split-v1`, `validate-patient-split-v1`, `materialize-patient-split-v1` y `freeze-patient-split-v1` rechazan `--dataset-version-id` por argparse, exit 2, antes de usar DB.

La excepción es `generate-patient-split-v1 --dataset-version-id`, pero ese flag **selecciona un DRAFT existente para dry-run**; no crea su ID. No admite seed nueva por CLI y no escribe asignaciones.

## 5. Prueba B — Persistencia: capacidad parcial acreditada; flujo público NO CERTIFICADO

### Esquema PostgreSQL actual, no inferido de migraciones

El esquema exportado y restaurado contiene:

- `dataset_versions`: PK `id`, UNIQUE `(name, semantic_version)`.
- `dataset_version_sources`: vínculos de una versión a la fuente existente.
- `dataset_split_assignments`: UNIQUE `(dataset_version_id, source_record_id)` y FK a versión, muestra y paciente.
- Trigger `enforce_dataset_assignment_consistency`: exige identidad/clase iguales a la fuente y un solo split por paciente **dentro de cada versión**; rechaza escritura de asignaciones sobre FROZEN.
- Trigger `enforce_dataset_version_lifecycle`: protege campos científicos de FROZEN y transiciones permitidas.
- `dataset_materializations`: UNIQUE `(dataset_version_id, attempt_number)` y FK a versión.

Estas estructuras permiten coexistencia, pero eso solo constituye una condición necesaria.

### Prueba de coexistencia real en instancia aislada

`test_B_E_two_versions_share_sources_but_preserve_distinct_assignments` crea una fuente **sintética**, 30 pacientes y 507 imágenes PNG, y dos UUID suministrados por el test. Usa el repositorio real `add_draft`, vincula ambos drafts a la misma fuente, carga perfiles mediante SQL real y optimiza con seeds 42/43. Inserta mediante `_bulk_insert`, respetando triggers activos.

Se comprueba que ambas versiones tienen exactamente el mismo conjunto de pares `(source_record_id, clinical_identity_id)`, asignaciones distintas, 507 registros, 30 pacientes, cero pacientes en más de un split y cero hashes duplicados entre splits. El test demuestra capacidad del esquema y primitivas, **no que la CLI haya creado esos UUID ni aceptado el split por su ruta pública**.

`test_B_failed_public_persistence_rolls_back_all_assignments` usa `persist_split_generation(..., APPLY)` real sobre la población sintética. La auditoría hardcoded de 27.558 falla; todas las inserciones se revierten y la versión permanece DRAFT con cero asignaciones. APPLY se usó solo contra `audit_fixture`, jamás contra la base operativa.

### Comportamiento sobre la versión operativa

La sonda READ ONLY llamó `prepare_split_generation(connection)` sin cambiar estado. Resultado reproducido dos veces:

```text
Split generation requires DRAFT or matching GENERATED state
```

La versión actual está FROZEN; el rechazo ocurre antes de optimizar. En `cli.py::persist_patient_split_v1`, la preparación se invoca **sin** pasar un UUID, de modo que selecciona v1. El comando no abre un draft alternativo. Una función de bajo nivel que permite SQL con otro UUID no elimina esta restricción del recorrido público.

## 6. Prueba C — Materialización: componente acreditado con contrato de raíz canónica

Código real probado:

```python
final_root = versions_root / str(plan.dataset_version_id)
materialization_id = uuid5(MATERIALIZATION_NAMESPACE,
                          f"{plan.dataset_version_id}:{attempt}")
relative_root = Path("malaria_dataset_versions") / str(plan.dataset_version_id)
```

Namespace de materialización: `ac72c2d7-44f1-55fc-9cb6-b49c0ed41e84`. El ID identifica versión+intento; no es un segundo nombre de `V1_ID`. Dos versiones con intento 1 producen IDs distintos.

La prueba `test_C_D_real_materializer_two_roots_ids_readback_idempotence_and_no_overwrite` llama **sin mocks** al materializador, con dos planes explícitos construidos por el fixture y `versions_root=<temporal>/data/malaria_dataset_versions`:

- Escribe realmente 507 PNG por versión y crea `train`, `val`, `test` y sus dos clases.
- Construye destinos `<versions_root>/<UUID_A>` y `<versions_root>/<UUID_B>`.
- Hace readback de los dos registros de materialización en PostgreSQL: UUID de versión/intento correcto, READY/PASS y 507 registros.
- Verifica que `<temporal>/data/<relative_root persistido>` coincide con el destino físico de cada versión.
- Repetir la misma preparación devuelve la misma materialización e `already_materialized=True`.

**Límite explícito:** el fixture provee el plan y avanza estados para preparar el escenario. No pasa por `build_materialization_plan`, que rechazaría ese digest y población; tampoco finge que el validador científico ha certificado 507 muestras. Es una prueba real del escritor físico y su persistencia, separada de la generación científica pública.

### Hallazgo sobre `relative_root`

El UUID no está hardcoded, pero el prefijo persistido sí lo está: siempre `malaria_dataset_versions/<UUID>`, independientemente de `versions_root`. `test_C_relative_root_assumes_canonical_parent` pasa una raíz temporal distinta; la escritura ocurre allí, pero el `relative_root` no representa esa ubicación bajo el data root esperado. El test pasa porque acredita esta limitación.

Por tanto, el registro de ruta es correcto **bajo el contrato que usa actualmente la CLI**, cuya raíz es `malaria_dl_local_project/data/malaria_dataset_versions`. No se certifica que acepte cualquier raíz y persista correctamente su ubicación. Cambio mínimo: validar el ancla canónica o calcular el relativo desde un data root explícito; no añadir otro resolutor.

Además, el plan público exige estado VALIDATED; una nueva llamada CLI sobre v1 FROZEN no alcanza automáticamente la rama idempotente del escritor. La idempotencia del escritor no implica idempotencia de toda la CLI.

## 7. Prueba D — Aislamiento: acreditado para versiones/planes válidos distintos

La misma prueba C/D:

1. Materializa A con su ID explícito.
2. Congela la versión sintética A mediante el lifecycle existente, sin alterar triggers.
3. Toma snapshot de su fila, asignaciones y SHA de todos los archivos.
4. Materializa B desde las mismas fuentes y otra asignación.
5. Comprueba raíz e ID de materialización diferentes y snapshots de A idénticos.
6. Intenta una receta/manifiesto incompatible para B: recibe `MATERIALIZED_STATE_CONFLICT`.
7. Intenta UPDATE de asignaciones de A FROZEN: PostgreSQL lo rechaza por el trigger.

`test_D_existing_unregistered_destination_is_not_overwritten` crea un archivo centinela en un destino sin registro READY; el escritor devuelve `FINAL_ROOT_EXISTS_WITHOUT_READY_PASS` y conserva sus bytes.

Se probaron dos versiones en secuencia, destinos canónicos, conflicto de manifiesto e inmutabilidad FROZEN. No se hizo una prueba de carreras simultáneas entre procesos ni se certifica atomicidad general filesystem/DB ante cualquier crash. El lock inicial se libera antes de copiar los archivos; no debe presentarse esta prueba como garantía universal de concurrencia. Esto no altera el resultado principal: faltan identidad/generación pública para iniciar legítimamente B.

## 8. Prueba E — Reutilización científica: optimizador acreditado; pipeline NO CERTIFICADO

### Población operativa existente, sin escritura

`readonly_probe.py` carga mediante `load_patient_profiles(connection, V1_ID)` los mismos 201 pacientes VERIFIED y 27.558 registros de fuente. Ejecuta el optimizador puro con 42 y 43, verifica igualdad del conjunto de pacientes y ausencia de violaciones duras en ambos candidatos.

| Comprobación | Resultado |
|---|---|
| Pacientes / registros | 201 / 27.558 |
| Digest paciente seed 42 | `cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f` |
| Digest paciente seed 43 | `052197d4d88b7c82d37c138c61d60d6483c9664076889d23402a6ecf86d58150` |
| Pacientes cuyo split cambia | 70 |
| Violaciones duras seed 42 / seed 43 | `[]` / `[]` |
| Persistencia de estos candidatos | Ninguna |

La correspondencia fuente/paciente viene de los registros existentes; el optimizador asigna pacientes completos. El evaluador revisa completitud, presencia de clases y hashes duplicados entre splits. No se redescargaron imágenes, no se crearon identidades nuevas ni se reescribió el vínculo a la fuente.

La expansión/persistencia de **otra asignación** sí se ejercitó con la población sintética en la instancia aislada, incluyendo checks SQL de overlap cero y conservación exacta de pares muestra/paciente (§5). No se afirma que seed 43 de la población operativa haya sido persistida o materializada.

### Bloqueos ejecutados

- `test_E_public_preparation_blocks_alternate_population_digest`: la preparación pública rechaza el digest no aprobado y deja cero asignaciones.
- `test_E_bypassing_digest_still_hits_fixed_record_count`: incluso suministrando `expected_digest` al nivel bajo, la preparación exige 27.558 filas. El fixture es intencionalmente pequeño; este límite no sería por sí solo un obstáculo para reutilizar la misma población real.
- `test_E_validation_and_plan_reject_new_assignment_digest`: sobre asignaciones distintas ya insertadas en el fixture, validación formal y construcción del plan fallan con `PATIENT_ASSIGNMENT_DIGEST_MISMATCH`.
- La persistencia también fija `APPROVED_RECORD_ASSIGNMENT_DIGEST` y las distribuciones concretas de v1. El freeze vuelve a fijar ambos digests. Cambiar solo UUID o seed no permite completar la cadena.

No se necesita implementar un algoritmo de brillo/contraste/entropía para desbloquear este caso: el optimizador actual ya puede producir otra asignación válida. La brecha es de identidad, parámetros y contratos de persistencia/validación/materialización.

## 9. PostgreSQL operativo y conservación de v1

Readback actual:

| Objeto | Resultado |
|---|---|
| Versión Cell | `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, FROZEN, 27.558 registros |
| Materialización Cell | `e15dc166-1c4b-558e-b77b-727b1783430c`, READY/PASS |
| `relative_root` | `malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` |
| Versiones totales | 2: Cell y Full Smear; no apareció una nueva versión |
| Materializaciones totales | 1; no apareció otra materialización |
| Asignaciones totales | 28.523 = 27.558 Cell + 965 Smear |
| Archivos de v1 | 27.558; 331.987.597 bytes |
| SHA-256 del inventario de archivos | `85538a4f2c443864697c952407e26007d7aa72aac73c9d5a43a2cc4a2ff012c8` |

Las dos lecturas de auditoría coinciden exactamente en los conteos y hashes de **todas las columnas de todas las filas** de once tablas: `datasets`, `clinical_identities`, `dataset_source_records`, `identity_evidence`, `dataset_versions`, `dataset_version_sources`, `dataset_split_assignments`, `dataset_split_validation_checks`, `dataset_split_statistics`, `dataset_materializations` y `dataset_materialization_activations`. Se incluyen por tanto ambas familias, no solo v1.

Para cada tabla, se ordenó `to_jsonb(row)::text` y se acumuló SHA-256 con separador LF. Para el árbol físico, se ordenó por ruta y se acumuló `relative_path + NUL + SHA256(bytes) + LF`. El JSON adjunto conserva los once hashes y los resultados de los candidatos. La segunda salida completa fue idéntica a la primera, verificada con una aserción Python; no se infirió integridad solo por conteos.

Estas lecturas y el aislamiento del ensayo documentan la conservación operativa durante las comprobaciones. No se pretendió validar la tolerancia a escritores externos concurrentes: cada lectura tuvo snapshot SQL propio. La demostración antes/después de una materialización B se realizó dentro del fixture aislado (§7).

## 10. Restricciones hardcoded y cambio mínimo

| Restricción | Localización | Efecto / cambio mínimo propuesto |
|---|---|---|
| Nombre, semver y namespace v1 producen siempre el mismo UUID | `persistence/bootstrap.py`, constantes y `apply_scientific_bootstrap` | Mantener bootstrap v1 como importación de fuente/historia. Añadir creación explícita de un draft de split con identidad propia y vínculo PRIMARY a la fuente existente. No alterar identidades de muestras/pacientes. |
| Se requiere versión existente; repositorio no inventa identidad | `repositories.py::add_draft`, `split_generation.py::prepare_split_generation` | La operación de nuevo split debe crear/persistir UUID una vez y pasarlo a toda la cadena. Puede usar un UUID nuevo por solicitud persistida, con idempotencia de reintento; no deducir que cada ejecución técnica debe crear una versión. |
| CLI solo dry-run para generación; escrituras sin selector UUID | `cli.py`, parsers y funciones v1 | Exponer operación de creación y selector explícito para persistir/validar/materializar/congelar la nueva versión. Propagar exactamente ese ID; nunca cambiar v1 para reusarla. |
| Seed 42 literal y metadata seed 42 | `prepare_split_generation`, `_methodology` | Leer la seed del contrato del draft y conservarla en metodología; el optimizador existente ya acepta seed. |
| Digests aprobados globales | `split_generation.py`, `formal_validation.py`, `materialization.py`, `governance/freeze.py` | Calcular, registrar y verificar fingerprints propios por versión. Las constantes v1 siguen protegiendo v1; no sustituirlas globalmente por los digests del segundo split. |
| Distribuciones exactas v1 | `persist_split_generation`: 22.180/2.693/2.685 imágenes; 161/20/20 pacientes; counts clase/perfil | Validar contra población y candidato aprobado del nuevo draft, manteniendo invariantes de completitud, identidad, clases y fuga cero. No imponer la distribución final de otro experimento. |
| 27.558 registros y 201 pacientes | Bootstrap, generación, persistencia, validación/materialización/freeze | Para esta misma población son valores correctos y no justifican quitar validaciones. Vincularlos al contrato de población, distinguiéndolos de asignaciones que sí cambian. |
| Prefijo `relative_root` fijo aunque raíz de escritura sea parámetro | `materialize_dataset_version` | Validar raíz canónica o derivar relativo de un ancla explícita; mantener destino por UUID y protección de destino existente. |
| Plan requiere VALIDATED, escritor tiene idempotencia propia | `build_materialization_plan`, `materialize_dataset_version` | Definir reintentos por estado/identidad sin descongelar ni reescribir versiones. No prometer idempotencia de CLI a partir de una sola función. |

No hace falta una nueva tabla para representar una segunda versión de esta población. Reutilizar `dataset_versions`, `dataset_version_sources`, `dataset_split_assignments`, checks, materializaciones y lifecycle. No duplicar fuentes ni pacientes, no crear resolutores paralelos ni guards de compatibilidad del esquema. Estas son propuestas; **ninguna se implementó**.

## 11. Matriz de certificación y pruebas posteriores necesarias

| Prueba solicitada | Dictamen preciso |
|---|---|
| A — UUID nuevo automático | **NO CERTIFICADO.** Fórmula/constantes v1 y ausencia de creación de draft nuevo acreditadas. |
| B — Coexistencia persistida | **Capacidad parcial demostrada** en PostgreSQL actual replicado, mediante fixtures y primitivas. **Flujo público NO CERTIFICADO.** |
| C — Ruta/ID materialización | **Componente demostrado** con UUID recibido y raíz canónica. Fuera de esa raíz el relativo no representa el destino real. El plan público bloquea otro split. |
| D — Directorios separados / anterior intacta | **Demostrado en ensayo secuencial aislado**, con dos versiones y planes explícitos, hashes antes/después, centinela y trigger FROZEN. No certifica un generador público inexistente. |
| E — Misma población y otra asignación | **Optimizador demostrado** sobre población operativa en memoria; linaje/coexistencia/fuga cero en fixtures PostgreSQL. **Cadena de persistencia/validación NO CERTIFICADA.** |
| Resultado integral | **NO CERTIFICADO.** No existe hoy el recorrido solicitado completo. |

Para certificar tras una futura corrección, una prueba end-to-end aislada deberá usar **los entrypoints públicos**, sin `add_draft` ni `MaterializationPlan` construidos manualmente por el test: crear una nueva identidad, reutilizar fuente/pacientes existentes, persistir asignaciones realmente distintas, validar, materializar, congelar y leer de vuelta versión/materialización/relative_root. Deberá verificar la versión anterior FROZEN y sus archivos antes/después, y comprobar reintentos sin duplicación ni cambio de identidad. Mantener las pruebas de conflictos/rollback/anti-leakage y añadir el caso de raíz incoherente corregido.

No corresponde ejecutar ese recorrido en PostgreSQL operativo antes de corregirlo y obtener la autorización requerida. El dictamen NO no está bloqueado por falta de permiso: está sustentado en fallos y restricciones concretas del código actual.

## 12. Pregunta final obligatoria

**¿Si ejecutamos hoy `malaria_dataset_split_project` para generar un segundo split Single-cell, obtendremos un `dataset_version_id` nuevo, una materialización independiente y una ruta `malaria_dataset_versions/<nuevo_dataset_version_id>/`, sin modificar la versión actual?**

**NO.** El bootstrap calcula nuevamente `V1_ID`; la generación necesita un DRAFT preexistente y la ruta de persistencia pública selecciona v1, hoy FROZEN, por lo que rechaza la operación. Aunque el optimizador admite otra asignación y el materializador puede escribir dos UUID en carpetas independientes, los contratos de persistencia, validación, plan y freeze siguen fijados al split v1. El soporte del esquema y del escritor físico no certifica el flujo completo.
