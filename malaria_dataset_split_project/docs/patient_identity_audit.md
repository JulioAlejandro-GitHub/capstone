# Auditoría de Patient-ID y leakage histórico — SPLIT 1B

## 1. Objetivo

Determinar con evidencia verificable qué Patient-ID corresponde a cada una de las
27.558 células y medir independencia entre `train`, `val` y `test`, sin crear un split
nuevo ni modificar datos, PostgreSQL, TRAIN o EVALUATE.

## 2. Fuente TFDS

Se inspeccionaron `features.json`, `dataset_info.json`, los TFRecords locales y el builder
instalado de `tensorflow_datasets/malaria:1.0.0`. Cada record publicado contiene sólo:

- `image`: `uint8`, forma `(None, None, 3)`;
- `label`: `ClassLabel` de dos clases.

TFDS no expone filename, Patient-ID ni example key dentro del record. El builder, sin
embargo, recorre los PNG oficiales y usa internamente `folder + "_" + file_name` como
key de generación; esa key no forma parte de las features serializadas. La
[ficha oficial TFDS](https://www.tensorflow.org/datasets/catalog/malaria) confirma la
estructura `image/label`, un solo split de 27.558 registros y la fuente NLM.

## 3. Fuente original

El caché local de descarga conserva los 27.558 PNG originales bajo:

`data/tensorflow_datasets/downloads/extracted/ZIP.../cell_images/{Parasitized,Uninfected}`.

NLM publica oficialmente `cell_images.zip` y dos CSV de Patient-ID↔células en su
[índice público](https://data.lhncbc.nlm.nih.gov/public/Malaria/index.html). La
[datasheet de LHNCBC](https://lhncbc.nlm.nih.gov/LHC-research/LHC-projects/image-processing/malaria-datasheet.html)
describe esos CSV expresamente como mappings Patient-ID a células. Las copias locales
de auditoría tienen SHA-256:

- parasitized: `d0367e513397404e980baee2a641bce9ce329a22e62ea9007962dfca2f8418d3`;
- uninfected: `a8577b21e7154724f4bbd18326218e2c63a99b22ab372b79a7530d36df6dab78`.

## 4. Evidencia oficial de Patient-ID

La evidencia primaria es metadata oficial explícita (nivel 1): cada fila contiene un
Patient-ID y la lista exacta de filenames asignados. Los CSV cubren 27.558 filenames
únicos, sin ausencia ni asignación a múltiples pacientes.

No se usa un parser de prefijos del filename. Aunque los nombres suelen comenzar por
un código similar al Patient-ID, la convención sintáctica por sí sola no se considera
demostrada ni necesaria: la asignación procede del CSV oficial.

El artículo primario informa que las células provienen de thin smears Giemsa de
pacientes y que la evaluación original se hizo a nivel paciente
([Rajaraman et al., 2018](https://peerj.com/articles/4568.pdf)).

## 5. Método de mapping

La relación se construyó en O(N):

1. Parsear los dos CSV oficiales como `source_filename → set(patient_id)`.
2. Decodificar cada PNG original a RGB y calcular
   `width × height × channels + SHA-256(pixels)`.
3. Crear un índice `decoded_pixel_key → source record(s)`.
4. Recorrer `files_manifest.csv` en su orden original. Ese orden fue generado durante
   el mismo recorrido TFDS y representa `tfds_index` implícito.
5. Calcular la misma clave para la imagen física y exigir exactamente un source record,
   una clase compatible y un Patient-ID oficial.

Resultado: 27.558 claves únicas, cero colisiones, cero duplicados exactos y mapping
uno-a-uno completo. El matching de píxeles es evidencia nivel 4 para relacionar el
artefacto físico con el original; el Patient-ID final proviene de evidencia nivel 1.

## 6. Jerarquía de evidencia

El resolver aplica: metadata oficial explícita → convención oficial documentada → match
exacto de artefacto → hash exacto de píxeles → unresolved. Si existen varios source
records o pacientes en el mejor nivel, produce `CONFLICT`; nunca elige el primero.
Filename sin metadata oficial no produce `VERIFIED`.

## 7. Cobertura

| Estado | Registros | Porcentaje |
|---|---:|---:|
| VERIFIED | 27.558 | 100 % |
| UNRESOLVED | 0 | 0 % |
| CONFLICT | 0 | 0 % |

## 8. Registros unresolved

No se observaron registros `UNRESOLVED` en esta materialización y con estas copias
oficiales. La política y tests preservan el estado para fuentes incompletas futuras.

## 9. Conflictos

No hubo `MULTIPLE_SOURCE_MATCHES`, `MULTIPLE_PATIENT_MATCHES` ni conflictos de clase o
metadata. Los CSV mapearon cada filename a un único Patient-ID.

## 10. Pacientes únicos

| Conjunto | Patient-ID únicos |
|---|---:|
| Total | 201 |
| Train | 201 |
| Val | 201 |
| Test | 201 |

Los CSV oficiales observados contienen 151 IDs asociados a células parasitadas y 201 a
células no infectadas; su unión es 201. La datasheet web actual describe otra cifra para
el dataset thin-smear de imágenes completas (193: 148+45). Esta discrepancia entre
artefactos oficiales se documenta, pero no altera el mapping explícito y exhaustivo de
los CSV específicos del single-cell dataset auditado.

## 11. Células por paciente

- mínimo: 65;
- máximo: 702;
- media: 137,1044776;
- mediana: 85.

El detalle completo por Patient-ID (`total_cells`, conteos por clase y por split) queda
en `var/audit/patient_identity_audit.json`, marcado `DERIVED AUDIT ARTIFACT` e ignorado
por Git.

## 12. Clases por paciente

- sólo parasitized: 0 pacientes;
- sólo uninfected: 50 pacientes;
- ambas clases: 151 pacientes.

## 13. Patient overlap histórico

| Intersección | Pacientes |
|---|---:|
| train ∩ val | 201 |
| train ∩ test | 201 |
| val ∩ test | 201 |

- en un solo split: 0;
- en exactamente dos splits: 0;
- en los tres splits: 201.

Por tanto, `PATIENT_LEAKAGE_CONFIRMED=YES`: el split histórico contiene observaciones
de un mismo paciente en conjuntos diferentes, no cumple independencia a nivel paciente
y sus métricas pueden estar influidas por correlaciones intra-paciente. Este hallazgo no
demuestra memorización ni cuantifica cuánto cambiarían las métricas con un nuevo split.

## 14. Células afectadas

| Conjunto | Células de pacientes con overlap |
|---|---:|
| Train | 22.046 |
| Val | 2.756 |
| Test | 2.756 |
| **Total** | **27.558 (100 %)** |

## 15. Identidades secundarias

Los features TFDS y CSV oficiales no proporcionan campos verificables `sample_id`,
`smear_id` ni `slide_id`; sus estados son `NOT_AVAILABLE` y cobertura 0 %. El filename
incluye segmentos de adquisición, pero no se promueven especulativamente a identidades.
Tampoco existen `laboratory_id` o `microscope_id` por record. La publicación primaria
documenta Giemsa como tinción a nivel del dataset (`STAIN_METADATA_STATUS=AVAILABLE`),
no como protocolo/ID granular por célula.

## 16. Validación manual y limitaciones

Se revisaron manualmente diez `VERIFIED` de distintas clases, splits y pacientes. Para
cada uno se comprobó existencia de ambos archivos, igualdad de hash RGB y pertenencia
del filename al Patient-ID en el CSV oficial. Muestra:

| # | Split | Clase | Patient-ID | Fuente |
|---:|---|---|---|---|
| 1 | train | uninfected | C57P18thinF | C57P18thinF_IMG_20150729_104027_cell_128.png |
| 2 | val | uninfected | C46P7ThinF | C46P7ThinF_IMG_20151130_210938_cell_144.png |
| 3 | train | parasitized | C103P64ThinF | C103P64ThinF_IMG_20150918_164331_cell_187.png |
| 4 | train | uninfected | C73P34_ThinF | C73P34_ThinF_IMG_20150815_111302_cell_6.png |
| 5 | train | uninfected | C78P39ThinF | C78P39ThinF_IMG_20150606_103459_cell_121.png |
| 6 | train | parasitized | C126P87ThinF | C126P87ThinF_IMG_20151004_104651_cell_1.png |
| 7 | val | uninfected | C105P66ThinF | C105P66ThinF_IMG_20150924_100655_cell_93.png |
| 8 | test | uninfected | C47P8thin_Original_Motic | C47P8thin_Original_Motic_IMG_20150714_093806_cell_131.png |
| 9 | train | parasitized | C148P109ThinF | C148P109ThinF_IMG_20151115_112855_cell_256.png |
| 10 | train | parasitized | C91P52ThinF | C91P52ThinF_IMG_20150821_124504_cell_204.png |

Limitaciones: `tfds_index` es posicional y no una feature estable publicada; la auditoría
depende del manifest histórico para conservar ese orden. Los CSV son oficiales pero no
incluyen schema/header ni IDs secundarios. No se verificó información clínica externa ni
se consultó PostgreSQL.

## 17. Conclusión científica

Sí, en los activos disponibles puede asociarse cada una de las 27.558 células con un
Patient-ID mediante evidencia oficial y mapping determinístico. El split histórico tiene
los 201 pacientes en sus tres particiones y el 100 % de las células pertenece a pacientes
que cruzan splits.

## 18. Implicancias para el nuevo split

`patient_id` está listo como campo de agrupación para diseñar persistencia y un futuro
split independiente por paciente. Los CSV/JSON de esta auditoría no deben convertirse
en source of truth definitivo: SPLIT 2 deberá preservar la fuente, versión, checksum,
evidencia y conflictos dentro del modelo científico PostgreSQL. No se materializó ni se
diseñó aquí un nuevo Train/Val/Test.

