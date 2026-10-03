# S1.2 — Canonical NLM Patient Identity

Estado documental: `HISTORICAL_AUDIT`. Fecha: 2026-10-03.
Resultado: **criterios técnicos S1.2 cumplidos**. S2 no ejecutada. La clave canónica es una identidad técnica cross-source basada en la convención nominal NLM; no certifica que se trate de la misma persona biológica clínicamente verificada.

## A. Estado Git inicial

Rama `s1-smear-segmentation-source-adapter`, árbol limpio antes de cambios.
HEAD `1e962fa22770f366f5aef13e5cd55956ee6c5f85`.
Parent `cf8fa58c93768d866e5402e81f9131ff34f50fde`.
Evidencia: `git_initial.json`. `git_at_execution.json` corresponde al inicio de la ejecución de auditoría, después de implementar código, y no reemplaza ese estado inicial.

## B. Arquitectura inspeccionada

Se inspeccionaron `identity/source_identity_index.py`, `patient_identity_resolver.py`, `identity_evidence.py`; `sources/thin_blood_smears_pf.py` y `polygon_set.py`; `persistence/repositories.py`, `smear_source_ingest.py`; `splitting/patient_profiles.py` y `patient_group_stratified_v1.py`; el documento S1 y los REPORT S1.1/S1.D. Las clinical_identities, identity_evidence y assignments se observaron mediante el snapshot SELECT-only ya usado en S1.1.

El loader Cell existente lee los CSV oficiales con `csv`/`ast.literal_eval`; conserva Patient-ID con el trim de espacio CSV existente. La resolución histórica de TFDS usa igualdad de píxeles para recuperar el filename y luego metadata oficial. S1.2 reutiliza directamente el loader oficial; no vuelve a ejecutar esa recuperación de imágenes.

La implementación mínima reside en `identity/nlm.py`. El helper S1 `cell_images_candidate_identifier` delega ahora en el parser estricto. `SmearSourceRecord.canonical_nlm_patient_key` expone la clave técnica; `patient_id` y las claves de procedencia conservan el directorio original. No se cambia el esquema persistido, los UUID existentes ni el estado clínico. El algoritmo genérico sigue recibiendo perfiles/identificadores opacos y no contiene reglas NLM. La conexión futura entre clave y gobernanza se decidirá en S2.

Los repositorios actuales permiten lecturas de versiones/fuentes, pero no exponen el snapshot integral ni este join de assignments. Se reutiliza `scripts/audit_s1_1/db_snapshot.py`, con guard SELECT y `default_transaction_read_only=on` desde la conexión, aislamiento REPEATABLE READ y verificación `SHOW transaction_read_only`. No se invocan rutas de escritura de repositorios.

## C. Fuentes de Patient-ID

- Cell: `malaria_dataset_split_project/var/audit/source/patientid_cellmapping_parasitized.csv` y `patientid_cellmapping_uninfected.csv`, gobernados por `config/current_split.yaml`; unión calculada de 201 IDs. Se compara exactamente contra las identidades de las fuentes vinculadas a la versión protegida.
- Full Smear: directorios físicos bajo `malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf/{Polygon Set,Point Set}`: 193. No se usa el CSV de auditoría como fuente de verdad.
- Anotaciones por paciente: workbook oficial local `Dataset_statistics.xlsx`. Los conteos se concilian con cinco JPG y cinco GT por directorio; no se interpretan ni validan los polígonos.
- Split: consultas actuales de PostgreSQL para `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, con fingerprints freeze coincidentes. Los CSV producidos aquí son evidencia derivada.

## D. Regla Cell → canonical

`canonical_nlm_cell_patient_key(official_patient_id, official_patient_ids=...)` valida pertenencia al conjunto obtenido del loader existente y devuelve exactamente el mismo string. No cambia case, sufijos, números ni fusiona aliases. Un identificador desconocido produce `ValueError`. No se duplica el parser CSV ni se infiere por filename o visión.

## E. Regla Full Smear → canonical

`canonical_nlm_full_smear_patient_key` usa `re.fullmatch`, extrae el grupo `canonical` y falla con `ValueError` fuera de la gramática. Ejemplo real: `234C92P53ThinF` → `C92P53ThinF`. La pertenencia a Cell se verifica después y de manera independiente: aceptar sintaxis no prueba existencia en el dataset.

## F. Gramática NLM observada

Prefijo: exactamente tres dígitos ASCII, primero no cero. Observado: 193 valores únicos, rango 142–380, con huecos; significado semántico no documentado. Los números C/P son positivos, sin ceros iniciales. El case y los sufijos se conservan.

```text
N := [1-9][0-9]*
FullSmear := [1-9][0-9]{2} Canonical
Canonical := C N (
    P N (ThinF | thinF | NThinF | N_ThinF | _ThinF |
         thinF_original | thin_Original_Motic | ReThinF |
         thinOriginalOlympusCX21 | thin_original)
  | A P N thinF
  | ThinF | thin_original | NThinF | NthinF
)
```

La gramática describe formas observadas, no un catálogo universal ni un rango numérico que demuestre membresía. Se rechazan rutas, filenames, whitespace, saltos de línea, dígitos Unicode, sufijos arbitrarios y nombres sin prefijo. Las 15 formas y frecuencias calculadas son:

| Forma (números sustituidos por #) | Directorios |
|---|---:|
| `#C#AP#thinF` | 1 |
| `#C#NThinF` | 7 |
| `#C#NthinF` | 1 |
| `#C#P#NThinF` | 11 |
| `#C#P#N_ThinF` | 9 |
| `#C#P#ReThinF` | 1 |
| `#C#P#ThinF` | 104 |
| `#C#P#_ThinF` | 6 |
| `#C#P#thinF` | 12 |
| `#C#P#thinF_original` | 2 |
| `#C#P#thinOriginalOlympusCX#` | 1 |
| `#C#P#thin_Original_Motic` | 1 |
| `#C#P#thin_original` | 1 |
| `#C#ThinF` | 34 |
| `#C#thin_original` | 2 |

`OlympusCX21` es un literal en el parser, aunque la visualización resumida sustituye 21 por #.

## G. Auditoría de 193 Full Smear IDs

193 source IDs; 193 parseados; 0 fallos; 193 claves generadas y distintas; 0 colisiones. 965 JPG y 965 GT; cinco parejas por ID. Mapping exacto igual al calculado en S1.1, comprobado por pares ID/clave y no solo cardinalidad. Evidencia: `full_smear_identity_mapping.csv` y `canonical_identity_summary.json`.

## H. Auditoría de 33 Polygon IDs

33 directorios; 33 claves distintas; 33 matches Cell; 0 fallos/ambigüedades técnicas; 165 imágenes y 165 archivos GT. `polygon_existing_split.csv` contiene las 33 filas solicitadas. El join no crea asignaciones.

## I. Intersección Full Smear ↔ Cell

Full Smear = 193; Cell = 201; intersección = 193; Full-only = 0; Cell-only = 8. Los ocho, recalculados desde las fuentes reales, coinciden con S1.1:

`C1_thinF`, `C203ThinF`, `C204ThinF`, `C206ThinF`, `C207ThinF`, `C209ThinF`, `C33P1thinF`, `C37BP2_thinF`.

## J. Excepciones

No hay colisiones, IDs inválidos ni excepciones que activen STOP en la población real. No se detectan pacientes con asignaciones en múltiples splits. NO_ASSIGNMENT = 0. La incertidumbre biológica persiste: el estado es `MATCHED_BY_NLM_NAMING_CONVENTION`; no se afirma crosswalk clínico explícito publicado por NLM. S1.1 preserva su conclusión clínica UNRESOLVED; S1.2 añade una frontera técnica autorizada, sin elevar esa evidencia a certeza clínica.

## K. Caso C47P8

| Full Smear ID | Canonical key | Set | Split Cell |
|---|---|---|---|
| 146C47P8thin_Original_Motic | C47P8thin_Original_Motic | Polygon | TRAIN |
| 148C47P8thinOriginalOlympusCX21 | C47P8thinOriginalOlympusCX21 | Point | TRAIN |

Se conservan ambos IDs. No se transforma 201 → 200 ni se resuelve identidad biológica. Ambos permanecen en TRAIN en la política candidata.

## L. Distribución Polygon TRAIN/VAL/TEST

| Split existente | IDs | % IDs | Full Smears | Polígonos | RBC parasitized | RBC uninfected | WBC |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 28 | 84.8485% | 140 | 28340 | 1057 | 27236 | 47 |
| VAL | 2 | 6.0606% | 10 | 2063 | 35 | 2026 | 2 |
| TEST | 3 | 9.0909% | 15 | 3861 | 50 | 3809 | 2 |
| TOTAL | 33 | 100% | 165 | 34.264 | 1.142 | 33.071 | 51 |

NO_ASSIGNMENT = 0. Anotaciones obtenidas del workbook; no se valida geometría ni correspondencia crop→polígono.

## M. Distribución 193 Full Smears TRAIN/VAL/TEST

| Split Cell | IDs Full Smear | % IDs | Imágenes | Anotaciones P | Anotaciones U | WBC |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 154 | 79.7927% | 770 | 6435 | 150754 | 218 |
| VAL | 19 | 9.8446% | 95 | 765 | 19085 | 30 |
| TEST | 20 | 10.3627% | 100 | 752 | 18872 | 23 |
| NO_ASSIGNMENT | 0 | 0.0000% | 0 | 0 | 0 | 0 |

Total: 193 IDs, 965 imágenes, 7.952 anotaciones P, 188.711 U y 271 WBC. Aquí se suman Point y Polygon: **no todos esos objetos son polígonos**. `full_smear_existing_split.csv` permite reproducir la agregación.

## N. Evaluación de política SAME SPLIT

La política candidata `canonical key → mismo split Cell/Smear` es técnicamente viable: mapeo único, cobertura total y asignación única por paciente. Evita separar entre familias las adquisiciones nominalmente relacionadas, sin afirmar identidad clínica demostrada. Mantener familias en splits distintos no demostraría independencia biológica.

La distribución completa es cercana a 80/10/10, pero el subconjunto Polygon tiene solo 2 pacientes VAL y 3 TEST. Sus 10 y 15 imágenes son observaciones correlacionadas dentro del paciente, no 25 unidades independientes. TRAIN tiene 20 pacientes con anotaciones parasitized; VAL 2; TEST 2 (un tercer paciente tiene cero anotaciones parasitized). Esto describe etiquetas, no diagnósticos clínicos.

En RBC Polygon, parasitized representa 3,736% TRAIN, 1,698% VAL y 1,296% TEST. VAL contiene 35 positivos y TEST 50; el desequilibrio y escaso número de pacientes limitan precisión, diversidad y estabilidad de métricas. VAL: C52P13thinF (30 P) y C57P18thinF (5 P). TEST: C49P10thinF (43 P), C235ThinF (0 P), C169P130ThinF (7 P). La mayoría de positivos de cada evaluación depende de un único paciente. Son conjuntos útiles para evaluación inicial conservadora, con resultados por paciente y limitaciones explícitas; no justifican por sí solos una estimación robusta de generalización clínica. Añadir tiles no aumenta el número de pacientes independientes.

Las cinco imágenes de cada Full Smear ID deben heredar una única asignación. En S4 todos sus tiles deben heredarla también; nunca random split de tiles. S2 deberá decidir la política y su suficiencia científica antes de persistir, sin alterar el split Cell protegido.

## O. Tests y reproducción

- `make test-canonical-nlm-identity`: **32 passed**. Identidad Cell, determinismo, gramática válida/inválida, C47P8, 193 casos reales S1.1, intersección oficial; auditoría sobre RAW actual y snapshot real, no mutación de inputs, STOP por conteos protegidos inconsistentes, identidad ausente, colisiones y Full-only.
- `make test-dataset-source-regression`: **35 passed, 1 skipped**. Adapter S1, Polygon parser, familias y freeze. El skip existente es sensibilidad a case en filesystem macOS.
- `make test-canonical-nlm-regression`: **19 passed**. Resolver Cell y estrategias/optimizador patient-level existentes.
- Total: **86 passed, 1 skipped, 0 failed**. Logs individuales adjuntos. No se ejecutan tests de integración que escriban PostgreSQL.
- `make audit-canonical-nlm-identity`: recalcula datos desde RAW, CSV y PostgreSQL actual. Requiere Docker backend activo y fuentes locales gobernadas. No descarga ni modifica fuentes; produce evidencia bajo esta carpeta. La auditoría falla ante condiciones STOP; `STOP.json` registra el error. En otra revisión, conservar la evidencia previa antes de ejecutar si se requiere historial de snapshots.

## P. Integridad

```text
PostgreSQL writes = 0
protected Cell Dataset Version changed = NO
Cell assignments changed = 0
Full Smear RAW files changed = 0
Dataset Versions created = 0
Full Smear assignments created = 0
YOLO datasets created = 0
tiles created = 0
```

Estos ceros describen exclusivamente las operaciones ejecutadas por S1.2; no son una afirmación sobre todas las escrituras de procesos externos. Las conexiones ejecutan solo SELECT/SHOW bajo READ ONLY. Snapshot antes/después igual, fila completa protegida igual, fingerprints freeze iguales, hashes integrales de tablas científicas iguales. Se conservan en `db_before.json.gz`/`db_after.json.gz` los digests de todas las tablas leídas y las filas necesarias para reproducir el join; se omiten las filas extensas ajenas al join.

`input_hashes_before.json`/`input_hashes_after.json` conservan SHA-256 por ruta, con igualdad exacta de inventarios: 27.558 archivos Cell protegidos; 2.022 archivos RAW (2.021 de distribución/documentos más manifiesto S1.D); dos CSV oficiales. Se hashean bytes, sin decodificar imágenes ni localizar crops. La versión conserva TRAIN 22.180 / VAL 2.693 / TEST 2.685 = 27.558.

No ingest, bootstrap, migraciones, freeze/unfreeze, cambios de fingerprints, nuevos assignments, Dataset Versions, S2, YOLO, tiles ni matching visual. El código genérico de split no se modifica.

## Q. Git final

Rama, HEAD y parent iguales al inicio. Sin commit ni push. `git_final.txt` contiene `git status --short --untracked-files=all` y lista exacta de archivos creados/modificados. Modificados: Makefile, docs/README.md y sources/thin_blood_smears_pf.py. Creados: identity/nlm.py, tests/unit/test_nlm_identity.py, scripts/audit_s1_2/{audit.py,test_audit.py} y los artefactos de esta carpeta. `git diff --check` sin errores.

## R. Recomendación técnica para S2

**A — YES:** los 33 Polygon IDs se convierten inequívocamente a claves técnicas NLM.

**B — 33/33:** existen en Cell.

**C — TRAIN = 28, VAL = 2, TEST = 3**, respectivamente 84,8485%, 6,0606% y 9,0909%; 140/10/15 imágenes.

**D — Viable técnicamente, con suficiencia científica limitada:** recomendar SAME SPLIT como política conservadora candidata contra cross-family leakage. S2 debe aceptar explícitamente la baja diversidad de VAL/TEST y su escasez de positivos o estudiar una ampliación compatible con la gobernanza. No redistribuir Cell, no confundir Point con polígonos y no compensar los pocos pacientes mediante separación aleatoria de imágenes/tiles. S1.2 deja evidencia para esa decisión; no crea Thin Blood Smear Patient Split v1.
