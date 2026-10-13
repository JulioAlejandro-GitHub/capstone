# C2.13 — Validación experimental mini CPU/GPU

Estado documental: `HISTORICAL_AUDIT`. Fecha: 2026-10-04.

**Estado: C2.13-A (Preflight) COMPLETO — pendiente aprobación explícita del usuario.**
No se han iniciado entrenamientos, no se han creado campañas, no se han modificado
archivos productivos ni el venv. Árbol de trabajo limpio en `d6babf5` (`main`).

Este documento es el entregable del preflight C2.13-A (brief §20). Las etapas
C2.13-B (CPU), C2.13-C (GPU), C2.13-D (comparación) y C2.13-E (auditoría) quedan
**pendientes** de la aprobación explícita del preflight y de la decisión Option A/B (§9).

## 1. Objetivo del preflight

Verificar, antes de cualquier entrenamiento, que el protocolo C2.13 es ejecutable de forma
reproducible y trazable sobre el dataset oficial, con los invariantes científicos intactos
(§4) y sin modificaciones productivas (§8). No se busca el mejor modelo ni se optimizan
hiperparámetros: se valida el **proceso experimental** (brief §2).

## 2. Diseño experimental (propuesta, pendiente aprobación)

Cuatro RUN organizados en campañas de **un solo miembro** (1 modelo × 1 optimizador ×
1 semilla × 1 variante):

| RUN | Dispositivo | Calibración | Campaña |
|---|---|---|---|
| C2.13-A | CPU | `none` | nueva identidad |
| C2.13-B | CPU | `threshold_grid` | nueva identidad |
| C2.13-C | GPU | `none` | nueva identidad — **bloqueado, §5** |
| C2.13-D | GPU | `threshold_grid` | nueva identidad — **bloqueado, §5** |

**Por qué un miembro por campaña (corrección al handoff anterior):** el protocolo es de
nivel de campaña (un único `calibration.algorithm`) y la política congelada de
`expand_matrix` (`campaigns/contracts.py`) fuerza `calibrate_threshold = (algorithm !=
"none")` sobre **todos** los miembros. Dos miembros (none + threshold_grid) en una misma
campaña son imposibles. → 4 campañas (o 2 si GPU queda bloqueado), cada una con
`max_members=1, max_attempts_per_member=1`.

**Reutilización de checkpoint (preferencia brief §4.5):** no es soportada por la
arquitectura actual — `execution/train.py` hace fit → selección → calibración → evaluación
final en un solo flujo; no existe modo "evaluar solo". → Se usan RUN independientes con
inicialización/orden/configuración equivalentes (el brief lo permite explícitamente). La
equivalencia de pesos entre los dos RUN del mismo dispositivo se **verificará** en
C2.13-D, no se asume.

## 3. Configuración científica efectiva

Calculada con `expand_matrix(frozen=True)` y contajes reales del dataset. Ambas campañas
comparten el mismo request; difieren únicamente en `calibration.algorithm`.

**Request (matriz):** `models=["custom_cnn"]`, `optimizers=["adam"]`, `seeds=[47]`,
`variants=[{name:"c213_mini", selected:{}, by_model:{custom_cnn:{execution:{max_epochs:3,
batch_size:64, deterministic_ops:false, no_augment:false, min_class_fraction:0.05,
reject_prediction_collapse:true}}}}]`, `exclusions=[]`.

| Campo | C2.13-A (`none`) | C2.13-B (`threshold_grid`) |
|---|---|---|
| `configuration_hash` | `3844a37f…f390905` | `6be0a66a…a1783ef9` |
| `calibrate_threshold` | `false` | `true` |
| `evaluate_best_on_test` | `false` | `false` |
| `max_epochs` | 3 | 3 |
| `min_recall` / `target_recall` | 0.98 | 0.98 |
| `min_specificity` | 0 | 0 |
| `beta` | 2.0 | 2.0 |
| `fine_tune_epochs` | 0 | 0 |
| `restore_best_weights` | true | true |
| `early_stopping` (patience / min_delta) | true (12 / 1e-05) | true (12 / 1e-05) |
| Optimizador | adam, lr 1e-4 | adam, lr 1e-4 |
| Modelo | 200×200×3, rescale_0_1, weights none, dropout 0.4, l2 1e-4, head 128, batch_norm train, fine_tune_layers 0 | (idéntico) |
| Miembro | seed 47, `expected_count` 1 | seed 47, `expected_count` 1 |

La semilla **no** forma parte de la configuración (pertenece al miembro); el worker inyecta
`execution.seed=47` en runtime, como muestran las configuraciones de sesión de B1.

**Protocolo (ambas campañas):** version `c213_derived:<algo>`, objective "Sensitivity
strictly > 0.98, then specificity; exploratory VAL", metrics {primary [sensitivity,
specificity], secondary [f2, roc_auc, average_precision], definitions_version
`capstone_science_e7_v1`, compliance point_estimate}, sensitivity_target 0.98,
specificity_minimum 0, roles {train, selection=val, calibration=val, final_test=test},
ranking {val, [auc_with_min_recall], [configuration_hash asc]}, checkpoint
{auc_with_min_recall, val_f2_parasitized, max, 0.5}, early_stopping {true,
val_f2_parasitized, max, 12, 1e-05, true}, calibration {`<algo>`, val, …}, budget {1,1},
missing report_all_members, retries first_verified_attempt, fallback diagnostic_only,
test_access final_only_after_candidate_lock, limitations {shared_val,
independent_calibration:false, test_exposure:"unknown"}, pending [].

## 4. Invariantes científicos (verificados)

### TEST excluido (triple bloqueo)
- El protocolo fuerza `evaluate_best_on_test=False`; `train.py` lanza `TEST_FORBIDDEN` en otro caso.
- `test_access = final_only_after_candidate_lock`.
- Calibración `population=val` (`validate_calibration_split` rechaza test).
- La propia configuración de sesión de B1 confirma `evaluate_best_on_test: false`.

### B1 protegido (verificado en BD)
- Campaña `b54ea684-1b0c-421d-a4b2-9f12667bd619` "Campaña 1": estado `finalized`
  (creada 2026-10-02, actualizada 2026-10-04); 12 miembros, todos `verified`.
- C2.13 crea **nuevas** identidades de campaña; cero escrituras sobre B1.
- No se reutilizan sus RUN, ni se modifican sus thresholds, métricas ni checkpoints.

## 5. Disponibilidad CPU/GPU

### CPU — OK
- venv `.venv-local-train`: Python 3.12.13, TensorFlow 2.17.1 (CPU), keras 3.15.1,
  numpy 1.26.4, SQLAlchemy 2.0.53, psycopg 3.3.5, psutil 6.1.1, python-dotenv 1.2.3.
- Máquina: Apple M4 Max (Mac16,5), 16 núcleos, 48 GB, 313 GiB libres.

### GPU — BLOQUEADO
- `tf.config.list_physical_devices("GPU")` → `[]`; sin módulo `pluggable_device`; sin
  directorio `tensorflow-plugins` en el venv. No hay dispositivo Metal disponible.
- Por brief §5.2/§17: se detiene **exclusivamente** el experimento GPU y se reporta el
  bloqueo. No se sustituye silenciosamente por CPU.

**Opciones para el usuario (§9):**
- **Option A (recomendada):** solo CPU → 2 campañas (C2.13-A none, C2.13-B threshold_grid).
  Estado final esperado: **APROBADO PARCIALMENTE** (solo CPU). Cero cambios de código.
- **Option B:** habilitar GPU → requiere (1) un venv separado con TF 2.17.1 +
  tensorflow-metal 1.1.0 y (2) un cambio mínimo y documentado en `local_launch.py`
  (hoy `VENV = ".venv-local-train"` está hardcodeado, línea 16). Instalar metal en el
  venv existente contaminaría los RUN CPU (el plugin se auto-carga al importar TF).

## 6. Dataset

- Versión oficial: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` "Malaria Patient Split v1"
  v1.0.0, **FROZEN** 2026-08-18, 27.558 registros.
- Materialización: `e15dc166-1c4b-558e-b77b-727b1783430c`, intento 1, **READY**,
  reconciliación **PASS**.
- Particiones (verificadas en BD): TRAIN 22.180 / VALIDATION 2.693 / TEST 2.685;
  pacientes 161 / 20 / 20 (split por paciente, sin mezcla).
- Huellas de la materialización: `patient_assignment_digest = cbe7a7b8…20ea7f`,
  `record_assignment_digest = 9709ce48…196ea2`.
- **Subconjunto imposible:** `dataset_integrity.verify_integrity` exige igualdad exacta del
  conjunto sellado de archivos + sha256 por archivo; un directorio de subconjunto fallaría
  con `DATASET_CONTENT_SET_MISMATCH`. Crear una nueva versión de dataset está prohibida.
  → **Particiones completas** (22.180 train / 2.693 val), `max_epochs=3`.
- La raíz del dataset (ruta Docker `/app/…`) se mapea al host vía
  `governed_dataset.local_dataset_root`.

## 7. Costo y recursos estimados

Basado en los RUN reales de B1 (misma máquina): custom_cnn 44.1 / 49.4 / 83.5 / 93.6 min
(≈3.02–3.21 min/época).

- 3 épocas ≈ 10 min + sobrecarga (carga de datos, calibración, evaluación final) ≈
  **12–15 min por RUN**.
- 2 RUN CPU (Option A) ≈ **25–30 min** en total.
- Checkpoints: 5.15 MB/época → ≈15 MB por RUN. EarlyStopping (patience 12) no puede
  dispararse en 3 épocas → exactamente 3 épocas.
- GlobalGate: un solo TRAIN activo → los miembros se ejecutan secuencialmente (sin paralelismo).

## 8. Modificaciones necesarias

**Ninguna.** La ruta CLI (`src/campaign.py create --request X.json --protocol Y.json`)
acepta `threshold_grid` (el protocolo JSON se pasa directamente a `expand_matrix`/
`validate_protocol`, que admite `algorithm ∈ {none, threshold_grid}` + `population=val`).

La brecha del catálogo público (`campaigns/configuration.py catalog()` expone
`calibration.algorithm` como `fixed` = `none`) es el hallazgo C1 **H09**; queda documentado
y **no se corrige** (el brief prohíbe cambiar defaults globales). No es un bloqueante de C2.13.

## 9. Riesgos detectados

1. **3 épocas probablemente no alcanzan recall 0.98** → el checkpoint cae a la selección de
   fallback y la calibración `threshold_grid` emite la advertencia de objetivo no cumplido.
   Es **esperado y documentado**, no un bloqueante de aprobación (brief §9: la prueba
   comprueba el funcionamiento del sistema, no exige desempeño clínico productivo).
2. **`deterministic_ops=false`** → la equivalencia de pesos entre los dos RUN del mismo
   dispositivo es esperada pero **debe verificarse**, no asumirse (C2.13-D).
3. **GlobalGate de TRAIN único** → las campañas ejecutan sus miembros secuencialmente; no hay
   paralelismo. Afecta solo el tiempo total, no la validez.

## 10. Decisión pendiente y estado

**Se requiere la aprobación explícita del preflight y la elección Option A/B antes de
iniciar C2.13-B** (brief §20). Hasta entonces: no se inician entrenamientos CPU/GPU, no se
crean campañas, no se modifica el venv ni el código productivo.

| Elemento | Estado |
|---|---|
| C2.13-A Preflight | **COMPLETO** (investigación 100%) |
| Aprobación del usuario | **PENDIENTE** |
| Option A/B | **PENDIENTE** |
| C2.13-B (CPU) | pendiente de aprobación |
| C2.13-C (GPU) | bloqueado (sin Metal) — Option A lo excluye |
| C2.13-D (comparación) | pendiente |
| C2.13-E (auditoría) | pendiente |

**Recomendación:** Option A (solo CPU, cero cambios de código, APROBADO PARCIALMENTE).
