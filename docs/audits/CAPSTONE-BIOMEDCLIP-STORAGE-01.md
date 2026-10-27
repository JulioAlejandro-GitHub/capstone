# CAPSTONE-BIOMEDCLIP-STORAGE-01

Estado: CURRENT_DOC. Fecha: 2026-10-27. Base de código: `b71ed1e` más cambios previos
sin commit. Veredicto: **NO APROBADO para cierre integral del estado operativo**.
Las correcciones no destructivas están implementadas; la normalización de la versión
productiva requiere una operación autorizada y los assessments OpenCLIP no están implementados.

## 1. Resumen ejecutivo

Se leyó completo el documento `docs/architecture/capstone_scientific_artifacts_and_persistence.md`
y se contrastó con código, PostgreSQL y filesystem. No se ejecutaron INSERT/UPDATE/DELETE,
DDL, entrenamiento completo, evaluación clínica, movimiento/borrado científico ni commits.
SQL de observación usó READ ONLY/default_transaction_read_only; PREPARE sólo comprobó
los contratos sin ejecutar los INSERT preparados.

El TRAIN lógico real cumple el acuerdo. Sus cinco archivos existen y coinciden en tamaño
SHA-256. El backend activo no monta la caché externa registrada y no puede resolverlos.
La carga offline en el host con el entorno de incorporación sí funciona. Cinco de las
siete carpetas UUID están registradas en bases aisladas: deben conservarse aunque no
aparezcan en `malaria_experiments`. Las otras dos no se eliminan.

## 2. Arquitectura inicial y hallazgos

| Hallazgo | Evidencia | Resolución |
|---|---|---|
| TRAIN lógico correcto | `runs` training/completed; 0 épocas, dataset NULL, metadata false | Conservado |
| `models.metadata` declarativo | training_mode=logical; scientific_origin con repo/revisión; sin rutas | Sin SQL correctivo |
| Checkpoint productivo en caché host | `artifacts.path`, Docker sin ese montaje | Pendiente sustitución autorizada |
| Dependencias desde rutas duplicadas del perfil | `openclip_inference._dependencies` antes del cambio | El resolvedor productivo vincula roles con `artifacts`, valida hash/tamaño/status y mantiene perfil histórico |
| Resolvedor de versiones usaba ruta duplicada de versión | `ModelVersionResolver.resolve` | JOIN de ownership con artifacts, ruta registrada, portabilidad y controles de tamaño/hash/status |
| Registro permitía rutas externas permanentes | `pretrained.registration` | Nuevas incorporaciones copian al árbol TRAIN existente antes de registrar |
| Repetición no contrastaba todas las clases/roles | `register_external_model` | Contraste de class_mapping y conjunto de artefactos; roles únicos |
| Forma fija 224 en adaptador | `OpenCLIPClassifier.input_shape` | Dimensión desde config, manteniendo 224 para BiomedCLIP |
| UI confundía finalización con entrenamiento | Panel Stage 2 / detalle | `training_performed=false` muestra incorporación lógica |
| Error TypeScript previo en tarjeta celular | `classificationRun` fuera del alcance de DetectionCard | Framework pasado como prop; build PASS |
| Requisitos Alembic aún operativos | requirements, CI, Make, status, purge/reset y reconstrucción legacy | Retirados sin tocar tablas ni constraints |
| Assessments son Keras | `assessment/runtime.py`, `lineage.py` | Límite documentado; no se inventa soporte OpenCLIP ni un dataset TRAIN |

## 3. Identidad operativa reconciliada

- Modelo: `1cf3e462-c0f7-4f72-92fe-306b8aaaa203`, `biomedclip_zero_shot`,
  `model_type=zero_shot`, `framework=pytorch_openclip`, pretrained=true.
- Origen: `microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224`,
  revisión `9f341de24bfb00180f1b847274256e9b65a3a32e`.
- TRAIN: `31d27b2d-6e90-4530-a589-ae92c91281df`, `training/completed`,
  `total_epochs=completed_epochs=0`, duración 0, dataset NULL, training_performed=false.
- Versión: `3fd16a84-b5c7-442b-916b-e0438bb0f3e5`, candidate, lineage resolved.
- Release del RUN: productive_stage2. Se conserva; no se interpreta como validación clínica.
- Assessments de ese TRAIN: **0**. La prueba sintética de esta auditoría no creó ninguno.

La FK real `(checkpoint_artifact_id,training_run_id) → artifacts(id,run_id)` asegura
ownership. El trigger de versión exige un RUN training. Los triggers de artefactos y
versiones impiden mutar la identidad gobernada; no se deshabilitaron.

## 4. Cinco artefactos

Todos siguen registrados bajo `/Users/julio/.cache/capstone-biomedclip-01b/original/`.
Sus rutas completas, metadata y comparación física están en
[evidencia JSON](CAPSTONE-BIOMEDCLIP-STORAGE-01-evidence/storage.json).

| Artifact ID | Rol | Bytes | SHA-256 | Física host |
|---|---|---:|---|---|
| `c7949e20-f933-4dcd-b34d-c6a924b7f8b5` | model_config | 707 | `9a41f334a8c444678772c0ebb9ab854c97ab350bced3a17b803e258d39c23dc0` | PASS |
| `e5e67ccf-6403-4dfa-b472-31920f4f2346` | checkpoint | 783705670 | `52cc993c5c5ff962bd0c60931874bc001e7e9b41666a385530f4a036294576be` | PASS |
| `2595973d-35e4-44eb-91b9-d5b84d29ae29` | text_config | 385 | `56bab767c02bc792897638feb8addc06d483d9c73769a5f554bbabea1f5507a1` | PASS |
| `e6174c50-faf7-42aa-a713-81ea7fb10811` | tokenizer_config | 28 | `53b6f42b8b8daddbdc6d3532c324187a92b46c1602bd6e8d4ad5a413b4fc90e1` | PASS |
| `8d18ee56-9655-4232-9677-da9efd6c9272` | vocabulary | 225062 | `7b36651908a88bc38bda41b728b2a598191e0d3b553cbacf7b1e5f026d5b5b9f` | PASS |

## 5. Directorios y plan de conservación

Cada directorio contiene los mismos cinco contenidos: 783.931.852 bytes por árbol.
Se calcularon los 35 SHA-256; todos coinciden con los cinco originales. Esto es suma
lógica de tamaños, no espacio físico recuperable: APFS puede compartir bloques.
Ninguno tiene RUN ni referencias en artifacts/model_versions/train_execution_sessions
operativos. Se amplió la consulta al contenedor aislado al encontrar una referencia
en `BIOMEDCLIP-01C-1_registro_zero_shot.md`.

| Directorio bajo outputs/train_runs | Base aislada con referencia actual | Integridad | Acción |
|---|---|---|---|
| `7b667ee5-edf0-4766-b77e-eec8a9add54c` | biomedclip_01c1 | 5/5 registrados; 5/5 iguales al origen | CONSERVAR |
| `56dc2663-b0a1-49c2-9691-a5b7fce260cc` | Sin referencia en las 8 bases consultadas | 0/5 registrados; 5/5 iguales al origen | REQUIERE INVESTIGACIÓN |
| `89f2cfd1-8987-4131-821f-d797e02daf9b` | biomedclip_01c1_final | 5/5 registrados; 5/5 iguales al origen | CONSERVAR |
| `91e3f4ca-266c-4621-bee3-d1d35e2f99f1` | biomedclip_01c1_verified | 5/5 registrados; 5/5 iguales al origen | CONSERVAR |
| `310bfe08-0a27-4cf7-a00c-4404f7284d75` | biomedclip_01c1_runtime | 5/5 registrados; 5/5 iguales al origen | CONSERVAR |
| `0560b627-1282-41cc-afcf-3542c1b63d17` | Sin referencia en las 8 bases consultadas | 0/5 registrados; 5/5 iguales al origen | REQUIERE INVESTIGACIÓN |
| `0616b9d7-aa13-4b2b-94a7-19d393324253` | biomedclip_01c1_concurrent | 5/5 registrados; 5/5 iguales al origen | CONSERVAR |

Se consultaron siete bases del contenedor `capstone_biomedclip_01c1_db` y la base
operativa. [Evidencia aislada](CAPSTONE-BIOMEDCLIP-STORAGE-01-evidence/isolated.json).
Los RUN aislados son training/completed, con cinco artifacts cada uno. Son evidencia
histórica de ensayos de incorporación; su metadata no se debe confundir con el contrato
operativo posterior. No se trasladó su esquema ni sus decisiones a producción.

`56dc2663…` y `0560b627…`: posibles remanentes de rollback, coherentes con el relato
histórico, pero la causa individual no está demostrada. Antes de declararlos candidatos
a eliminación se necesita cerrar referencias en backups y manifiestos de esos ensayos.
No hay un manifiesto de eliminación aprobado. Se conservan todas las carpetas.

## 6. Contrato de rutas y metadata

TRAIN por referencia usa outputs/train_runs; campañas coordinadas usan outputs/campaign_runs;
assessments usan artifacts/assessments. `local_scientific_path.ALLOWED_TREES` ya incluía
campaign_runs en el código inicial: el documento de 2026-10-21 estaba desactualizado.
Las rutas se resuelven desde registros, no desde nombres de modelos.

Las incorporaciones nuevas usan `incorporate_training_files` en el módulo compartido
storage_paths. Copia exclusiva, verificación antes/después, originales conservados.
Una transacción fallida puede dejar una carpeta nueva: se audita, no se borra automáticamente.
La repetición idempotente de la incorporación actual no mueve ni normaliza su histórico.

`models.metadata` es correcto. Hay ubicaciones redundantes en snapshots de versión y
preprocesamiento, ya gobernados. Se conservan como historia; la resolución efectiva de
las dependencias ahora viene de artifacts y se mantiene separada del snapshot en memoria.

## 7. CAPSTONE_LOCAL_TRAIN

Búsqueda en Python, tests, scripts, .env/ejemplos, Compose y documentación. Consumidores:
local_launch.bootstrap, persistence.database, backend database_safety, execution.accelerator;
además tests y comentarios de explain_agent. Historial del lanzador anterior a esta tarea
incluye `9e54cef`, `de4a487`, `cb4f7ae`.

1. Marca bootstrap local: admite 127.0.0.1:5432 hacia PostgreSQL Docker y exige GPU TF en host.
2. La detección Docker la hace `/.dockerenv`; la variable no crea una modalidad nueva.
3. No selecciona framework.
4. No selecciona almacenamiento.
5. Sólo afecta la conectividad del registro local; no determina training_mode.
6. Los comandos oficiales la reciben de bootstrap.
7. El soporte loopback del backend fue añadido previamente para herramientas en host;
   no se eliminó sin romper esos consumidores.
8. Sí introduce diferencias de conectividad y exigencia GPU entre entornos, intencionadas
   en el contrato existente. No se usa como prueba de PyTorch MPS.

Se conserva, con responsabilidad documentada. No hay bifurcación por nombre BiomedCLIP.

## 8. Framework y OpenCLIP

La selección productiva contrasta models.framework con la versión y despacha por
`resolved.framework=='pytorch_openclip'`. Keras conserva su cargador. No se usa el nombre
BiomedCLIP para escoger framework. El adaptador es reutilizable para configuraciones
OpenCLIP con texto HF local; no declara soporte para cualquier arquitectura arbitraria.

La carga verifica pesos y dependencias, usa configuración/texto/tokenizer locales,
`pretrained_text=False`, CPU/fp32, eval() e inference_mode(). Config de origen declara
`timm_model_pretrained=false`; no se descargó una revisión distinta. La prueba se hizo
con HF_HUB_OFFLINE=1 y TRANSFORMERS_OFFLINE=1.

Entorno de incorporación: Python 3.12, torch 2.14.1, torchvision 0.29.1,
open_clip_torch 3.3.0, transformers 4.57.6, timm 1.0.30, tokenizers 0.22.2.
MPS disponible=true; **dispositivo efectivo CPU**. Backend: torch 2.14.1+cpu,
OpenCLIP 3.3.0 y transformers 4.57.6. `.venv-metal` no tiene OpenCLIP.
[Evidencia de carga](CAPSTONE-BIOMEDCLIP-STORAGE-01-evidence/openclip-smoke.json).

La [prueba de ambos resolvedores](CAPSTONE-BIOMEDCLIP-STORAGE-01-evidence/resolver-smoke.json)
confirmó IDs de dependencias, identidad del checkpoint, snapshot intacto e igualdad exacta
entre el tensor del adaptador y el transformador original OpenCLIP.

No se instaló software ni se cambió selección de dispositivo. CPU conserva la política
previa reproducible. Habilitar MPS necesitaría su propia prueba de paridad y registro.

## 9. Preprocesamiento

SUPPORTED_PREPROCESSING vive en productive_model y lo consulta stage2_status.
El resolvedor valida compatibilidad framework/modo; CellClassificationService despacha
OpenCLIP y Keras explícitamente. La identidad está en el snapshot de model_versions,
deployment y snapshot de clasificación, no en lo que esté instalado accidentalmente.

OpenCLIP convierte RGB a CHW float32, usa tamaño/configuración registrados y los
transformadores OpenCLIP. Se verificó tensor 3×224×224 y scores finitos sobre imagen
sintética. Texto: archivos locales juntos, contexto 256, prompts y clases congelados.
No se equivale rescale con OpenCLIP. `rescale` sólo es alias de rescale_0_1 en el resolvedor
productivo; el núcleo de data.preprocessing no lo acepta como opción independiente.
VGG16 usa su transformación original; DenseNet conserva su contrato interno existente.

El runtime de assessments sigue siendo Keras; no se presenta la carga celular OpenCLIP
como prueba de EVALUATE/EXPLAIN/TEST científico. No se tocaron sus identidades.

## 10. Docker: revisión selectiva

| Cambio Docker | Origen | Necesario | Acción |
|---|---|---|---|
| scientific_storage → ./var/storage | Diff previo sin commit en compose; base b71ed1e | No se demostró que sea exclusivo de BiomedCLIP; backend activo usa el bind clínico | Conservar: volver al volumen cambiaría el almacenamiento clínico visible |
| Dependencias OpenCLIP en Dockerfile | Diff previo sin commit, documentado en MODEL-CONTRACT-01B | Sí para inferencia OpenCLIP dentro del backend | Conservar |
| docker-compose.openclip.yml, montaje de caché | Archivo previo sin seguimiento | Temporalmente necesario para las rutas antiguas, no para una incorporación nueva normalizada | No está aplicado al backend actual; no aplicarlo ni borrarlo silenciosamente |
| Montajes Alembic de override | Configuración previa para tests/históricos | No son requisito de arranque | Conservar archivos históricos; retirar gates y dependencia runtime |

**Reversiones Docker aplicadas: ninguna.** No se encontró un cambio cuya reversión
selectiva fuera a la vez necesaria y segura antes de resolver las referencias reales.
Compose config -q PASS. PostgreSQL healthy/pg_isready PASS. Backend /health HTTP 200.
No se reiniciaron servicios ni tocaron volúmenes. La afirmación histórica de que el backend
montaba la caché no describe el contenedor actual, creado sólo con base+override.

## 11. Alembic y SQL de activación

Retirados: dependencia en tres requirements, job de linealidad CI, comandos Make de
migración, ejecución de migrate.sh, consulta de revisión en db-status, requisito de alembic_version en backup, DDL histórico
en el fixture EXEC.1, gates de revisión
en purge/reset y mantenimiento. El campo histórico alembic_revision del manifiesto reset
se conserva como NULL, sin exigir head. Los tests históricos requieren Alembic sólo si
se instala expresamente.

La reconstrucción antigua de mantenimiento instalaba DDL legacy y migraba a 20260922_01:
se retiró su bootstrap y las entradas db/all fallan antes de detener servicios. Su código
original permanece en Git. No se reemplazó por otro mecanismo de reconstrucción.
Se conserva clasificación de recursos, ownership, backups y guards de integridad.
Los diagnósticos históricos execution/schema.py, alembic/, alembic_v2/ y adoption_v2/
permanecen, sin ser prerrequisitos del runtime. No se borró alembic_version.

`cell_activation_optional_evaluation.sql` cambia dos CHECK a num_nonnulls<=1 y actualiza
el trigger del snapshot celular para permitir ausencia de evaluación y exigir coherencia
con publicación. No crea evaluación ni cambia run_type/release. No contiene preflight
histórico. Los dos CHECK ya están aplicados en la BD actual. Se conserva el archivo y
no se vuelve a ejecutar DDL. Su publicación es técnica, no validación clínica.

## 12. Correcciones y archivos

- Registro/dependencias: pretrained/registration.py, execution/storage_paths.py,
  models/openclip_inference.py, governance/services/model_version_resolver.py.
- Consumo: backend services/productive_model.py y cell_classification.py.
- UI/contrato: schemas/stage2_status.py, services/stage2_status.py, frontend types/api.ts,
  Stage2PublicationPanel.tsx, Stage2ReleaseDetail.tsx y CellReviewWorkspace.tsx.
- Alembic: requirements, .github/workflows/ci.yml, Makefile, scripts/db/{status,migrate,purge,backup},
  scripts/storage/reset_smear_analysis.py, scripts/maintenance/{database,orchestrator}.py.
- Pruebas focalizadas y fixtures actualizados; documentación de arquitectura/operación.

Estos archivos pueden contener cambios anteriores: el diff contra HEAD **no atribuye
todo a esta auditoría**. Se preservaron las modificaciones iniciales, incluyendo servicios
Stage 2, SQL previo y evidencia MODEL-CONTRACT-01B. No hubo git restore ni commit.

## 13. SQL entregado

- `scripts/sql/zero_shot_storage_audit.sql`: sólo lectura, identidad/procedencia/versiones,
  artefactos, checksums esperados, duplicados, publicación y constraints.
- `scripts/sql/zero_shot_incorporation.sql`: contratos INSERT preparados y deallocados,
  sin EXECUTE; escritor efectivo sigue siendo el repositorio existente.
- `scripts/sql/zero_shot_storage_pending_corrections.sql`: referencias y destinos propuestos;
  no contiene UPDATE ilegal de identidad. Sustitución pendiente de autorización.

SQL no prueba existencia de archivos del host: se combina con verified_file y el manifiesto
físico. No se inventan columnas ni se relajan FK para acomodar consultas.

## 14. Pruebas y límites de evidencia

[Comandos y evidencias reproducibles](CAPSTONE-BIOMEDCLIP-STORAGE-01-evidence/verification.md).

| Verificación | Resultado |
|---|---|
| Hash/tamaño cinco originales y 35 copias | PASS |
| Artefactos de cinco bases aisladas | 25/25 coinciden con archivos |
| Almacenamiento/resolvedor offline | 21 PASS, incluye repetición idempotente con repositorios simulados |
| Lanzador/acelerador y primeras pruebas de almacenamiento | 57 PASS, 1 omitida |
| Backend clasificación/Stage2/activación | 60 PASS, 13 omitidas por requerir integración |
| Herramientas PostgreSQL/purga/reset | 193 PASS |
| Regresión Keras/registro/configuración/assessments | 98 casos PASS: 95 iniciales + 3 reejecutados tras corregir entorno/fixtures |
| Frontend | 443 PASS; build TypeScript/Vite PASS tras corregir prop fuera de alcance |
| SQL alta | PREPARE/DEALLOCATE/ROLLBACK PASS en sesión READ ONLY |
| Compose/PostgreSQL/backend | config -q PASS; pg_isready PASS; /health 200 |

La regresión Keras incluye pasos mínimos y reload de Custom CNN/VGG16/DenseNet121,
no entrenamiento científico completo. Los tests de equivalencia usan imagen sintética.
Las primeras ejecuciones fallaron por PYTHONPATH y fixtures SimpleNamespace incompletos;
se documenta el ajuste, no se presenta ese primer intento como aprobado.
No se ejecutaron pruebas que escriban en PostgreSQL real, ni evaluaciones clínicas.
El test de idempotencia usa mocks: no certifica una nueva transacción real de incorporación.

## 15. Operaciones pendientes de autorización

1. Resolver la disponibilidad Docker del modelo vigente. La propuesta permanente es
   una incorporación/versionado de sustitución con archivos en el árbol compartido,
   conservando el RUN, versión, artifacts y archivos actuales.
2. Autorizar por separado el cambio de selección productiva mediante el servicio existente,
   después de verificar la nueva carga en backend. No actualizar paths protegidos ni snapshots.
3. Cualquier eliminación de carpetas exige otro manifiesto y autorización. Cinco árboles
   tienen referencias vigentes en bases aisladas; los otros dos siguen en investigación.

La exigencia de autorización proviene del prompt del usuario, §16: «UPDATE, INSERT o
DELETE en PostgreSQL real», «Movimiento de artefactos referenciados» y «Cambios de estados
productivos». No proviene de una skill ni de una revisión automática.

## 16. Riesgos, observaciones y veredicto

**NO APROBADO** para cierre integral: el modelo productivo sigue apuntando a archivos
inaccesibles desde el backend actual. El soporte científico EVALUATE/EXPLAIN/TEST OpenCLIP
sigue ausente y no debe inferirse de un smoke test celular. La normalización de nuevas
incorporaciones, la resolución por artefactos y las correcciones de código están verificadas
al alcance indicado; no se modificaron estados ni evidencia histórica para aparentar cierre.
