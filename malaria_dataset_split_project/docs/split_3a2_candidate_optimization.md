# Optimización y selección dry-run — SPLIT 3A.2

## 1. Algorithm contract final

Se utilizó sin cambios el evaluator/objective aprobado en 3A.1:

```text
algorithm: patient_group_stratified_v1 1.0.0
seed oficial: 42
randomization unit: clinical_identity_id
canonical order: source_identifier ASC, clinical_identity_id ASC
randomization: local random.Random(derived_seed).shuffle
hard gate: patient disjointness, completeness, valid splits,
           exact duplicate cross-split=0, both classes per split
objective: lexicographic representativeness, class balance,
           record ratios, patient ratios, canonical digest ASC
```

No se alteró `methodology_json`; SPLIT 3B debe registrar controladamente los parámetros
de este documento al persistir/regenerar el candidato.

## 2. Generación y optimización acotada

Se generaron 16 initial candidates. El primero es la baseline 3A.1; los otros 15 usan
permutaciones cuyas seeds se derivan matemáticamente de la seed oficial y se inicializan
cerca de los targets blandos de pacientes (round 80/10/10). Es una estrategia de
generación, no un constraint: moves pueden cambiar esos conteos si mejoran el objective.

Se ordenan los candidatos válidos con `candidate_sort_key`. Los cuatro mejores reciben
búsqueda local hasta 30 iteraciones por start, con 20 propuestas determinísticas por
iteración: MOVE en una de cada cuatro y SWAP en las restantes. Sólo se aceptan vecinos
que pasan el mismo hard gate y mejoran estrictamente objective+digest. El run ganador
evaluó 1.156 candidatos y ejecutó 57 iteraciones locales agregadas; la búsqueda siempre
es finita.

## 3. Baseline y ganador

Baseline seed 42:

```text
digest: 99269330938438e366485b190e667fbd1cf7ea1dd48bd0e7321ca3b90fa151ee
objective: (0.2290550838232092, 0.14758751182592245,
            0.08845344364612817, 0.06069651741293525)
```

Ganador dry-run no autoritativo:

```text
candidate id: candidate-cbe7a7b8c92d3761
digest: cbe7a7b8c92d3761076f64886765bc73dbea0a99808fb07f054a83494820ea7f
objective: (0.02081972566949705, 0.009497206703910632,
            0.004847957036069328, 0.0009950248756218638)
winner vs baseline: BETTER
```

El ganador reduce todos los niveles del objective, no sólo el primero.

## 4. Composición del ganador

| Split | Patients | Patient ratio | Records | Record ratio | Parasitized | Uninfected | Parasitized ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 161 | 0.800995 | 22.180 | 0.804848 | 11.137 | 11.043 | 0.502119 |
| val | 20 | 0.099502 | 2.693 | 0.097721 | 1.325 | 1.368 | 0.492016 |
| test | 20 | 0.099502 | 2.685 | 0.097431 | 1.317 | 1.368 | 0.490503 |

Perfiles: train 121 BOTH_CLASSES/40 UNINFECTED_ONLY; val 15/5; test 15/5;
PARASITIZED_ONLY es cero globalmente.

Tamaños por paciente:

| Split | Min | Max | Mean | Median |
|---|---:|---:|---:|---:|
| train | 65 | 702 | 137.764 | 84.0 |
| val | 66 | 687 | 134.650 | 87.5 |
| test | 68 | 568 | 134.250 | 90.5 |

Para BOTH_CLASSES, la proporción de records parasitized por paciente —no parasitemia—:

| Split | Min | Max | Mean | Median |
|---|---:|---:|---:|---:|
| train | 0.014286 | 0.901709 | 0.372410 | 0.288660 |
| val | 0.068493 | 0.896652 | 0.392624 | 0.403509 |
| test | 0.042857 | 0.882042 | 0.393903 | 0.345794 |

Val y test son comparables: 20 pacientes cada uno, diferencia de 8 records, diferencia
de ratio parasitized ≈0.00151, perfiles idénticos 15/5 y medias de tamaño separadas por
0.4 records.

## 5. Objective breakdown

| Componente | Valor |
|---|---:|
| patient profile deviation | 0.0012437811 |
| patient size representativeness deviation | 0.0208197257 |
| within-patient parasitized-ratio deviation | 0.0173498195 |
| representativeness (max anterior) | 0.0208197257 |
| class balance deviation | 0.0094972067 |
| record ratio deviation | 0.0048479570 |
| patient ratio deviation | 0.0009950249 |

Target vs actual:

| Metric | Target | Actual | Absolute deviation |
|---|---:|---:|---:|
| train records | 0.80 | 0.804848 | 0.004848 |
| val records | 0.10 | 0.097721 | 0.002279 |
| test records | 0.10 | 0.097431 | 0.002569 |
| train patients | 0.80 | 0.800995 | 0.000995 |
| val patients | 0.10 | 0.099502 | 0.000498 |
| test patients | 0.10 | 0.099502 | 0.000498 |
| max class ratio vs global 0.50 | 0.50 | 0.490503–0.502119 | 0.009497 |
| BOTH_CLASSES patient ratio | 151/201 | 121/161;15/20;15/20 | ≤0.001244 |

## 6. Hard constraint audit y legacy

El mapping contiene exactamente 201 patients y representa 27.558 records. Una mapping
funcional Patient→split implica cero multi-assignment y overlaps train/val/test. No hay
unassigned patients/records. PostgreSQL reporta cero grupos exactos duplicados y el
candidate gate reportó cross-split overlap cero. Todos los splits contienen ambas clases.

El legacy tenía 22.046/2.756/2.756 records y los mismos 201 pacientes en sus tres splits.
El ganador tiene 22.180/2.693/2.685 y patient overlap cero. El legacy no fue input del
algoritmo; la comparación demuestra la mejora metodológica sin exigir sus counts exactos.

## 7. Reproducibilidad

RUN A y RUN B reconstruyeron perfiles desde PostgreSQL y ejecutaron generación y
optimización desde cero. Ambos produjeron el mismo digest y objective. Seed 43 produjo
`052197d4d88b7c82d37c138c61d60d6483c9664076889d23402a6ecf86d58150`, confirmando
control real por seed; la seed oficial permanece 42.

## 8. Dry-run y contrato para SPLIT 3B

CLI:

```text
python -m malaria_split.cli generate-patient-split-v1 --dry-run
```

No se escribió artefacto de assignments: evita que un JSON derivado sea confundido con
autoridad. SPLIT 3B debe reconstruir con PostgreSQL+contrato, exigir digest ganador
`cbe7...ea7f`, volver a ejecutar hard audit y recién entonces persistir atómicamente las
27.558 assignments y transicionar DRAFT→GENERATED. Hasta entonces PostgreSQL conserva
assignments=0, v1 DRAFT y filesystem intacto.
