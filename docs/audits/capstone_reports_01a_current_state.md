# CAPSTONE-REPORTS-01A — Lectura EXPLAIN y navegación científica

Estado documental: `HISTORICAL_AUDIT`. Comprobación: **2026-10-13**, desde 15:16 UTC (12:16 America/Santiago). Código: `6061e4fcb802cac16ef16a3eeca0c5ee962797b2`; árbol inicialmente limpio. Auditoría de solo lectura; propuestas sin implementar.

Referencia leída: [CELL-EXPLAIN-01](cell_explain_01_readback_audit.md), evidencia **2026-10-08**. Este informe registra diferencias, no recertifica masivamente archivos. SELECT con psycopg en backend Docker, `default_transaction_read_only=on`; GET reales al proceso activo `127.0.0.1:8000`. No ejecuciones científicas, migraciones, cambios operativos ni lecturas de muestras/archivos TEST. Solo se consultaron metadatos agregados de intentos para inventariar métodos; los resultados y archivos inspeccionados son VAL. No se ejecutó navegador E2E ni suite con fixtures que pudieran escribir en BD.

## A. Resumen ejecutivo

**La exclusión de EXPLAIN del linaje y el rechazo explícito del hook fueron corregidos. Persisten el bloqueo HTTP y la desconexión del detalle TRAIN.** El detalle E6 ya muestra referencias paginadas, pero no resultados por muestra y solicita imágenes por ruta física.

Los cuatro GET de assessments siguen funcionando. El TRAIN de referencia ahora tiene **1 EVALUATE y 2 EXPLAIN**, ambos EXPLAIN de identidades distintas; no corresponde conservar el conteo histórico de cero explicaciones.

**Diferencia física relevante:** la carpeta del intento histórico `ceaa29af-cb60-4be2-8a67-01b9c9382cda` y su PNG representativo no existen en la ubicación registrada del host ni en su equivalente Docker. La BD conserva resultados, referencias y verificación. Esto demuestra indisponibilidad en esa ubicación, no prueba eliminación definitiva ni su causa. La certificación de sus 5.386 archivos del 8 de octubre sigue siendo HISTÓRICA. Otros PNG existentes de Grad-CAM, LIME y SHAP sí coinciden con los metadatos de BD; ninguno se sirve por ID.

## B. Matriz H1–H9

Los estados califican el hallazgo concreto; «CORREGIDO» no significa que toda el área esté terminada.

| Hallazgo histórico | Estado actual | Evidencia actual / archivos | Corrección necesaria |
|---|---|---|---|
| H1 — Persistencia E6 íntegra | CONFIRMADO ACTUAL en BD; NO VERIFICADO íntegro en disco | SELECT: 2.693 resultados, 2.693 map y 2.693 overlay; `verified`. Carpeta histórica ausente en host/Docker | Aclarar ubicación/disponibilidad del intento histórico; no regenerar ni cambiar referencias |
| H2 — CTE excluye EXPLAIN | CORREGIDO | `repositories/assessment_lineage.py:21`: ambos tipos; `services/lineage_children.py:289`: variante `assessment_explain_e6`; GET devuelve dos explicaciones | Reutilizar proyección diferenciada existente |
| H3 — Conteos mezclan/excluyen tipos | CORREGIDO en separación; PENDIENTE garantía por identidad | `services/lineage_children.py:76–80`, `training_summaries.py:66–72`: filtros por kind; `visible_assessments` conserva todos los intentos | Distinguir conteo de intentos de conteo de identidades; no ocultar historial |
| H4 — Endpoints assessments funcionales | CONFIRMADO ACTUAL | Cuatro GET 200; `routes/assessments.py`, `services/assessments.py`, `repositories/assessments.py` | Consumir API existente; no segunda API |
| H5 — Detalle TRAIN usa fuente histórica | PENDIENTE | `RunDetail.tsx:514`, `routes/runs.py:871,927,949`; GET explicabilidad vacío frente a dos E6 | Integrar selección explícita de intentos E6 |
| H6 — Hook rechaza EXPLAIN | CORREGIDO; detalle aún parcial | `useAssessment.ts:21` acepta ambos; `AssessmentDetail.tsx` discrimina; `AssessmentExplanationDetail.tsx` solo lee artefactos | Añadir resultados/metadatos y PNG por ID |
| H7 — verified no es bloqueo general | CONFIRMADO ACTUAL | Linaje devuelve `verified`; componentes conservan estado; `completed` permanece en TRAIN | No convertir estados |
| H8 — HTTP 403/404 | PENDIENTE | GET representativos actuales; `services/artifacts.py:30–38,109–126` solo catálogo histórico y raíces sin assessments | Resolver ID E6, pertenencia y raíz confinada; resolver además disponibilidad del caso histórico |
| H9 — Asociación EVALUATE opcional | CONFIRMADO ACTUAL | SELECT: `identity.evaluation=null`; mismo TRAIN/checkpoint/dataset/VAL | No inventar vínculo entre intentos |

Paths backend de la tabla relativos a `backend_api/app`; paths React relativos a `frontend/src`.

**Matiz H3:** `attempt_rank` se calcula pero no filtra `visible_assessments`. Cada intento se cuenta una vez, pero una identidad con reintentos se contaría varias veces. Hoy hay 5 intentos/5 identidades EVALUATE y 8/8 EXPLAIN: no hay duplicación real observada. La deduplicación histórica de EVALUATE utiliza `evaluations.source_assessment_attempt_id` y la identidad enlazada; no inventa runs E6. No hay deduplicación científica genérica EXPLAIN histórico/E6. El TRAIN auditado no tiene hijos `run_lineage`. Conservar historial de todos los intentos y añadir, si el reporte necesita conteo científico, `COUNT(DISTINCT identity_id)` separado; no aplicar silenciosamente `attempt_rank=1` ni alterar elegibilidad EVALUATE.

## C. PostgreSQL y endpoints

Abreviaciones: TRAIN=`bbbd5b60-afaa-4034-a504-a60ed642aafe`; EXPLAIN=`ceaa29af-cb60-4be2-8a67-01b9c9382cda`.

TRAIN existe, `training/completed`, dataset `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`. EXPLAIN conserva identidad `e27a118c-68f0-4edd-8a68-c29dd338dabc`, ordinal 1, estado `verified`, Grad-CAM clase 1/capa conv2d/VAL. Modelo y columna de identidad remiten al mismo TRAIN; checkpoint `4294d2b2-690b-5884-a3cb-fc7f0eb3653d`. La verificación registrada conserva `count=2693`, `sha256=1f552ccc9788f9ead484d7c0e078c60f11620a03e408d8d2bdb9dcfc561367d5`, `artifacts_hash=8cd3d213c1d87e6e6d707fdfb4414ac877988ab730a4d9eac44b08ce3c2780ef`. Son valores leídos, no hashes globales recalculados hoy.

| GET actual | Resultado |
|---|---|
| `/assessments?training_run_id=TRAIN` | 200; un evaluate y dos explain verified |
| `/assessments/EXPLAIN` | 200; identidad, TRAIN y verificación correctos |
| `/assessments/EXPLAIN/results?limit=1&offset=0` | 200; muestra `000f6007-9330-5085-972a-247631c541c6`, dos artifact IDs |
| `/assessments/EXPLAIN/artifacts?limit=2&offset=0` | 200; map y overlay de esa muestra |
| `/runs/TRAIN/lineage-children?datasource=malaria&limit=100` | 200; evaluation_count=1, explainability_count=2, total_count=3, truncated=false |
| `/runs/TRAIN/explainability?datasource=malaria&limit=1` | 200; items=[], total=0 |

El segundo EXPLAIN es `b3ce7093-4e3c-47d7-9e4e-83bc8bd04ea0`, identidad `a92104b2-b64d-4d62-aa96-58ac06a1eef3`; no mezclar sus resultados con el primero.

Lecturas acotadas reproducibles (parámetros enlazados):

```sql
SELECT id,run_type,status,dataset_version_id FROM runs WHERE id=:train;
SELECT a.id,a.identity_id,a.state,a.ordinal,a.verification,a.artifact_root,
       i.kind,i.training_run_id,i.identity->>'split',i.identity->'explanation',
       i.identity->'evaluation'
FROM assessment_attempts a JOIN assessment_identities i ON i.id=a.identity_id
WHERE a.id=:attempt;
SELECT count(*) FROM assessment_results WHERE attempt_id=:attempt;
SELECT role,count(*) FROM assessment_artifacts WHERE attempt_id=:attempt GROUP BY role;
SELECT payload FROM assessment_artifacts
WHERE attempt_id=:attempt AND role='overlay' ORDER BY sample_id LIMIT 1;
```

El repositorio de lectura ya fue separado de rutas/servicios y las rutas tienen `response_model`, aunque con diccionarios genéricos. No se necesita repetir esa refactorización.

## D. Artefactos y métodos

`/artifacts/file` sigue consultando exclusivamente `artifacts`. No une `assessment_artifacts` con su intento ni valida pertenencia E6. Prioriza ID; conserva confinamiento, extensiones de imagen, MIME real y `nosniff`. El rebase del sufijo `malaria_dl_local_project` existe, pero la raíz assessments no está autorizada.

Raíces activas: `/app/malaria_dl_local_project/{outputs,data}`, `/app/data`, `/app/data/prediction_uploads`, `/app/var/artifacts`, `/app/var/storage/model-explanations`. `LocalStorage.resolve/resolve_verified` ofrece confinamiento, rechazo de symlinks y validación tamaño/hash reutilizables; no hace falta usar sus escritores.

Docker inspeccionado: bind de `malaria_dl_local_project` a `/app/malaria_dl_local_project`, solo lectura. Compose y montaje real conservan esa estructura. El montaje está disponible, pero su contenido histórico no es equivalente al del 8 de octubre.

| Método / intento representativo | Evidencia actual VAL | HTTP por artifact_id |
|---|---|---|
| Grad-CAM histórico `ceaa29af-cb60-4be2-8a67-01b9c9382cda` | Directorio y PNG `15a1778c-4b74-4d5d-af96-40908a982baf` ausentes en rutas esperadas host/Docker | 404; por ruta macOS 403 |
| Grad-CAM `a1acbb5c-170e-437c-b310-f7be6cc671d9` | verified, 1 resultado/2 artefactos; PNG `ea5dd236-0f9c-4595-869e-fc34ea157a9f`, 35.712 bytes, tamaño/SHA coinciden | 404 |
| LIME `e7ef3690-b0cf-4c2f-8fdc-7255907fb245` | verified, 1/2; clase 1, num_samples=1000; PNG `34663c81-c06f-44fd-b862-6768865ee442`, 22.762 bytes, tamaño/SHA/firma PNG coinciden | 404; por ruta 403 |
| SHAP `24023051-41a3-4bf9-a2a7-25f771e2a4c8` | verified, 1/2; clase 1, num_samples=1000, background VAL; PNG `98cd7f34-2966-435d-9cfb-9ea0504d06f8`, 19.413 bytes, tamaño/SHA/firma PNG coinciden | 404; por ruta 403 |

Inventario actual: 4 intentos Grad-CAM verified; 2 LIME (uno verified y otro failed con 2.772 referencias parciales); 2 SHAP verified. Todos VAL y con la misma estructura `artifacts/assessments/<attempt_id>`. No extender la certificación de archivos de un intento a otros ni llamar verificado al LIME fallido. La UI tiene botón de overlay independiente del método, pero su URL por ruta queda bloqueada. NPY permanece evidencia científica, sin necesidad de renderizarlo.

## E. Frontend

`useAssessment` ya acepta `evaluate/explain`; `AssessmentDetail` usa variante EXPLAIN y enlace al TRAIN. `AssessmentVerification` permite `count`, `sha256`, `artifacts_hash` y métricas opcionales: ya no exige clasificación EXPLAIN. Falta una unión discriminada estricta; `identity.explanation` solo modela método, no clase/capa, y `AssessmentArtifact` omite sample_id/state.

`AssessmentExplanationDetail` + `useAssessmentArtifacts` leen 100 referencias por página y solo cargan la imagen al pulsar «Ver imagen»: existe paginación/diferimiento, no descarga automática de 2.693 PNG. Sin embargo:

- No existe cliente `/results` en `api.ts` ni presentación por muestra.
- Faltan clase, split, cantidad de resultados y artifacts_hash en el detalle EXPLAIN.
- Se muestra `artifact.path` y se envía como parámetro HTTP; debe usarse artifact_id y ocultarse la ruta física.
- La paginación actual cuenta artefactos, no resultados. No ofrece unión muestra→resultados→overlays.
- `getAssessments` existe, pero lista globalmente; falta parámetro `training_run_id` en el cliente para el detalle TRAIN.

`RunDetail` sigue sin consumir assessments; su mensaje «No hay casos de explicabilidad registrados para esta ejecución» resulta engañoso para este TRAIN. Confirmado por código y respuesta vacía de su fuente; no por captura de navegador.

## F. Navegación y cuatro bloques TRAIN

`.report-run-name` en `components/reports/RunSummaryRow.tsx` sigue siendo `<strong>`, UUID truncado y sin copiar. TRAIN tampoco tiene allí botón «Ver detalle». Convertir nombre a Link, mostrar UUID completo y botón copiar; pasar datasource desde `TrainingRunGroupCard`. `App.tsx` ya conserva datasource en navegación programática.

Las tarjetas `AssessmentEvaluationCard` y `AssessmentExplanationCard` ya navegan por attempt_id, preservan datasource y no lo tratan como runs.id. `Runs.tsx` diferencia claves `assessment:<attempt_id>`. Los históricos conservan run_id/status; E6 conserva attempt_id/state.

**Identificadores adicionales comprobados por SELECT y GET 200:**

- `4703ff9e-2d20-413f-9b9a-cd945c8dd632`: intento EXPLAIN verified, identidad `c7153332-3a49-49c9-8f75-77ad113d71c4`.
- `da1f46d6-0f17-46b0-8f51-9f0fcacf0c76`: intento EVALUATE verified, identidad `08b0b61e-8733-4c5c-9924-49ccc1e10a2f`.
- Ambos pertenecen a TRAIN `338136db-a207-47fc-bbf3-d17ce85c0dc2`, mismo checkpoint/dataset/VAL; `evaluation=null` en EXPLAIN. Son intentos distintos, no alias ni relación formal EXPLAIN→EVALUATE.

`App.tsx:96` espera `:attemptId` y `api.getAssessment` consulta ese ID. Mantener `/modelo-ia/evaluaciones/e6/<attempt_id>`.

| Bloque TRAIN | Fuente existente | Conexión mínima pendiente |
|---|---|---|
| Predicciones por imagen | `/runs/{run_id}/image-predictions`, tabla run_image_predictions, filtros/paginación | Selector EVALUATE E6 y `/assessments/{attempt}/results`; conservar fuente histórica identificada |
| Explicabilidad por caso | `/runs/{run_id}/explainability`, vista histórica | Selector EXPLAIN del TRAIN y resultados/PNG paginados del intento seleccionado |
| Métricas y reportes técnicos | métricas TRAIN, reportes/matriz históricos | Mostrar verification.metrics solo del EVALUATE seleccionado; hashes/count para EXPLAIN |
| Artefactos generados | detalle run + resumen histórico de artefactos | Referencias E6 paginadas, agrupadas por intento, PNG por ID y NPY como metadatos |

No combinar derivadas por posición, fecha o simple coincidencia de TRAIN; conservar identidad, checkpoint, dataset y split visibles.

## G. Configuración propuesta

`ARTIFACTS_ROOT` ya existe (`/app/var/artifacts` en .env); gobierna otro almacenamiento y no equivale a assessments. `STORAGE_ROOT` tampoco equivale. No se encontró `ASSESSMENT_ARTIFACT_ROOT` configurada.

Propuesta, **no aplicada**:

```dotenv
ASSESSMENT_ARTIFACT_ROOT=artifacts/assessments
```

Resolver respecto de `MALARIA_PROJECT_ROOT` estable, no cwd: en host, raíz de `malaria_dl_local_project`; en Docker, su mount existente. Una raíz para los tres métodos. Validar valor relativo y confinamiento; resolver referencias históricas mediante sufijo conocido y comprobar que pertenecen al artifact_root/intento registrados. No sobrescribir artifact_root, exponer paths, ampliar raíces arbitrariamente, copiar ni regenerar. No se necesita cambiar Compose según el montaje inspeccionado. Resolver una raíz no recupera por sí solo la carpeta histórica ausente.

## H. Plan mínimo REPORTS-01B

1. **Proyección:** conservar variante EXPLAIN existente; no quitar filtros ni reconstruirla. Probar identidad y estados separados. Documentar conteos de intentos y añadir conteo científico separado si se exige unicidad por identidad, manteniendo todos los intentos navegables.
2. **HTTP:** ampliar lectura por ID en `repositories/assessments.py` con join al intento; servicio valida referencia, raíz/intento, archivo regular y MIME; reutilizar FileResponse. Mantener seguridad actual y error explícito para contenido ausente.
3. **Detalle E6:** completar tipos/cliente/hook de resultados y discriminación EVALUATE/EXPLAIN. Mostrar método, clase, split, estado, count, hashes y muestras.
4. **Paginación:** reutilizar limit/offset existentes. Unir `result.artifacts[]` con `artifact_id` y corroborar sample_id. Los offsets de resultados y artefactos son independientes. Para páginas por muestra eficientes, extender opcionalmente filtros de la ruta de artefactos existente por sample_id/IDs; no descargar todo el catálogo ni suponer dos posiciones por muestra.
5. **TRAIN:** consultar intentos por training_run_id y ofrecer selección EXPLAIN; reutilizar detalle/galería paginada. No fabricar vínculo EVALUATE.
6. **Caso histórico ausente:** diagnóstico acotado de ubicación antes de aceptar PNG 200 para ese ID. No autoriza restaurar, copiar ni regenerar; entretanto preservar evidencia BD y mostrar indisponibilidad.

Archivos previstos: `backend_api/app/repositories/assessments.py`, `services/artifacts.py`, `config.py` (si centraliza la nueva variable), `.env.example` y configuración de entorno al implementar; `frontend/src/types/api.ts`, `services/api.ts`, `hooks/useAssessmentArtifacts.ts`, nuevo hook de resultados, `components/reports/AssessmentExplanationDetail.tsx`, `pages/RunDetail.tsx`. Ajustar `schemas/assessment_lineage.py`, `schemas/lineage_children.py`, `services/lineage_children.py`, `services/training_summaries.py` solo para contrato/conteos adicionales. `routes/assessments.py`/servicio/repositorio solo si se añaden filtros; `routes/artifacts.py` puede conservar contrato. No cambios previstos al pipeline científico, migraciones ni router.

## I. Plan mínimo REPORTS-01C

1. `RunSummaryRow.tsx`: Link en nombre, UUID completo y copiar con feedback accesible; `TrainingRunGroupCard.tsx` pasa datasource. Ajustar CSS únicamente para legibilidad.
2. Conservar enlaces E6 existentes y regreso a TRAIN; probar ambos UUID adicionales, sin sustituir uno por otro.
3. `RunDetail.tsx`: conectar los cuatro bloques según F, con selección explícita y estados carga/error/vacío por intento; reutilizar clientes/hooks de 01B. Evitar que una respuesta tardía muestre resultados del intento anterior.
4. Reutilizar `Runs.tsx`, router y App; modificarlos solo si las pruebas demuestran una brecha. No nuevas rutas ni reescritura de navegación ya corregida.

## J. Aceptación posterior

Pruebas automatizadas aisladas, orquestadas por Makefile/Docker durante implementación; no ejecutadas en 01A:

- Linaje/resúmenes: EVALUATE y EXPLAIN separados; reintentos de una identidad visibles sin inflar conteo científico; histórico enlazado no duplicado; estados verified/completed preservados; paginación consistente.
- Artefactos: ID E6 válido→200 image/png, tamaño/hash esperado, nosniff; ID inexistente→404; pertenencia a otro intento, traversal y symlink fuera de raíz rechazados; MIME inválido rechazado; NPY no renderizado. Raíz relativa independiente de cwd y rebase macOS→Docker confinado.
- React: EXPLAIN sin metrics válido; EVALUATE conserva métricas; resultados/artefactos con orden distinto y cardinalidad desigual se unen por ID; carga diferida; error y cambio de página/intento; no URL con path físico.
- Navegación: nombre TRAIN clicable, UUID íntegro/copiable, datasource conservado; cada tarjeta abre su attempt_id y vuelve al TRAIN; cuatro bloques sin mezclar derivadas.

Extender `backend_api/tests/test_lineage_children_api.py`, `test_training_summaries_api.py`, `test_artifacts_api.py`; `frontend/tests/e6-lineage.test.mjs` y `run-detail-explainability.test.mjs`. Usar target Makefile focalizado si la suite amplia escribe fixtures; frontend Docker disponible mediante `make test-exec1-frontend`. No ejecutar pruebas de entrenamiento ni datos TEST operativos.

Repetir los GET de C y los artifact_id de D tras implementar. Exigir 200 para PNG presentes y mensaje honesto de ausencia donde corresponda. Para certificar recuperación del intento histórico, su PNG también debe estar disponible y coincidir con BD; un PNG alternativo no satisface ese caso. Comprobación de navegador a través de localhost pendiente: verificar renderizado y navegación, no solo HTTP interno.

## K. Estado final

- **CONFIRMADO ACTUAL:** H1 en BD; H4, H7, H9; artefactos representativos existentes de los tres métodos.
- **CORREGIDO:** H2, separación de tipos H3, rechazo del hook H6 y enlaces E6 desde tarjetas.
- **PENDIENTE:** unicidad científica de conteos H3 frente a reintentos; H5; resultados/overlays por ID en H6; H8; enlace/UUID/copiar TRAIN.
- **NO VERIFICADO:** integridad física completa actual H1, causa/ubicación alternativa de la carpeta ausente, experiencia visual E2E. Integridad masiva del 8 de octubre: **HISTÓRICO**.

REPORTS-01A documentado; REPORTS-01B/01C no implementados. Solo se crean este informe y su entrada de índice documental.
