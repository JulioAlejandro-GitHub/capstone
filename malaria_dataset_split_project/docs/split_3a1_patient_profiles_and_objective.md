# Patient Profiles y contrato de optimización — SPLIT 3A.1

## 1. Alcance y población

Esta etapa prepara `patient_group_stratified_v1`; no elige candidato oficial, no escribe
assignments y no cambia lifecycle. PostgreSQL `malaria_experiments.public` es la única
autoridad. La v1 DRAFT contiene una fuente PRIMARY cuya población produce exactamente
201 perfiles, 27.558 records, 13.779 parasitized y 13.779 uninfected.

No se usan filesystem, split histórico o CSV para decidir el nuevo split. Los hashes
fuente persistidos se usan únicamente para el hard constraint de duplicados exactos.

## 2. Patient Profile

La unidad indivisible es `clinical_identity_id` de tipo PATIENT. Cada perfil contiene:

```text
clinical_identity_id
source_identifier
total_records
parasitized_records
uninfected_records
parasitized_ratio
uninfected_ratio
patient_class_profile
source_file_sha256 (colección para duplicate gate)
```

Los perfiles se cargan con `ORDER BY source_identifier ASC, clinical_identity_id ASC`.
Se observaron 151 BOTH_CLASSES, 50 UNINFECTED_ONLY, 0 PARASITIZED_ONLY; tamaños 65–702
(mediana 85). No existen variables persistidas para edad, sexo, hospital, laboratorio,
microscopio, severidad, parasitemia, slide, smear, país o tratamiento; ninguna se inventa.
La proporción parasitized por paciente describe etiquetas disponibles, no severidad ni
parasitemia.

## 3. Randomización controlada

Primero se aplica el orden canónico anterior y luego `random.Random(42).shuffle` sobre
una lista local. No se usa global random state, SQL sin ORDER BY, sets, orden de archivos
o timing. La unidad randomizada es siempre Patient. Igual población+versión de
algoritmo+seed produce la misma secuencia; otra seed puede producir otra secuencia.

Random no significa ganador random puro. La secuencia sirve para baseline, generación
inicial y futura exploración reproducible en 3A.2.

## 4. Hard constraints

El evaluador rechaza cualquier candidato que incumpla:

1. Patient disjointness: el mapping funcional Patient→un único split lo garantiza por
   representación; train/val/test son mutuamente excluyentes.
2. Completeness: las keys deben ser exactamente los 201 Patient-ID conocidos; por
   indivisibilidad esto cubre los 27.558 records sin multi-assignment.
3. Split name limitado a train/val/test.
4. Exact duplicate cross-split overlap cero, usando `source_file_sha256` PostgreSQL.
5. Presencia de parasitized y uninfected en cada partición.

Los targets 80/10/10 nunca son hard. PostgreSQL revalidó cero grupos de hashes exactos
duplicados antes de esta etapa, pero el gate permanece implementado para cualquier
candidato/población.

## 5. Soft objectives y normalización

Todos los componentes son desviaciones adimensionales donde menor es mejor:

- `patient_profile_deviation`: máximo error absoluto entre proporciones locales/globales
  de BOTH_CLASSES, UNINFECTED_ONLY y PARASITIZED_ONLY.
- `patient_size_deviation`: máximo error relativo de la media de records/paciente local
  respecto de la media global.
- `within_patient_parasitized_ratio_deviation`: máximo error absoluto de la media local
  de `parasitized_ratio` entre perfiles BOTH_CLASSES respecto de su media global.
- `representativeness_deviation`: máximo de los tres anteriores; evita compensaciones.
- `class_balance_deviation`: máximo error absoluto de la proporción parasitized local
  respecto de la global.
- `record_ratio_deviation`: máximo error absoluto entre proporción de records y target.
- `patient_ratio_deviation`: máximo error absoluto entre proporción de pacientes y target.

La comparación es lexicográfica, sin suma ni pesos mágicos:

```text
LEVEL 0 hard constraint gate
LEVEL 1 representativeness_deviation
LEVEL 2 class_balance_deviation
LEVEL 3 record_ratio_deviation
LEVEL 4 patient_ratio_deviation
LEVEL 5 canonical assignment digest ASC
```

Val y test participan simultáneamente en cada máximo y poseen el mismo target 0.10; no
se construye uno como residuo privilegiado del otro.

## 6. Candidate evaluator

`evaluate_candidate(profiles, patient_assignments)` es puro y devuelve valid/invalid,
violaciones, métricas por split, todos los componentes, objective tuple y digest. Las
métricas incluyen pacientes, records, clases, perfiles, media de tamaño y media de
proporción parasitized para BOTH_CLASSES. SPLIT 3A.2 debe reutilizar este evaluador sin
cambiar escalas o prioridades.

## 7. Representación canónica, digest y tie-break

El assignment se ordena por `clinical_identity_id` textual y serializa una línea
`clinical_identity_id|split_name` por paciente, unidas con newline. El SHA-256 UTF-8 es
`CANONICAL_ASSIGNMENT_DIGEST`. Dos mappings con distinto orden de inserción producen el
mismo digest. Ante objective tuples iguales gana digest lexicográficamente menor; nunca
“first encountered” implícito.

## 8. Baseline

La baseline ordena y mezcla pacientes con seed 42, y luego asigna cada paciente completo
al split que minimiza lexicográficamente el máximo error global proyectado de records y
pacientes. El desempate usa train/val/test canónico. Una reparación determinística mueve
pacientes completos, sólo si fuese necesario, para asegurar presencia de ambas clases
sin vaciar esa clase en el donor.

La baseline real pasó todos los hard constraints. Es sólo referencia/initial candidate:
no es el candidato oficial, no se persiste y su calidad no se presume óptima.

## 9. Interfaces y pruebas

Módulos:

```text
splitting/patient_profiles.py
splitting/candidate.py
splitting/objective.py
splitting/patient_group_stratified_v1.py
```

Auditor read-only:

```text
python -m malaria_split.cli audit-patient-profiles-v1
```

Las pruebas cubren perfiles reales y sintéticos, orden canónico, misma/otra seed,
baseline completa, class presence, duplicate gate, objective, digest y tie-break. El
test PostgreSQL confirma cero assignments antes/después.

## 10. Contrato exacto para SPLIT 3A.2

3A.2 recibirá los 201 perfiles canónicos, generará candidatos Patient→split usando sólo
PRNG local seed 42 y estrategias documentadas, pasará cada candidato por el hard gate,
ordenará candidatos válidos con `candidate_sort_key`, y seleccionará un ganador sólo con
la regla objective+digest fijada aquí. No podrá seleccionar pacientes manualmente,
randomizar source records, cambiar componentes, usar atributos no persistidos o convertir
80/10/10 en constraint exacto.

Al cierre de 3A.1 v1 continúa DRAFT y tiene cero assignments, statistics, checks,
materializations y activations. No existe ganador oficial ni materialización física.
