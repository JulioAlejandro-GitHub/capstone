# U1B — Pseudo-máscaras para U-Net: comparación experimental

- Dataset: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` (Malaria Patient Split v1, FROZEN), solo **TRAIN**.
- Aislamiento: rama `exp/u1b-pseudo-masks` en un worktree propio. No se tocó TEST, `malaria_physical_split`, PostgreSQL (solo lectura), el pipeline TRAIN ni la campaña activa.
- Código: `scripts/experiments/unet_masks/` (`masks.py`, `sample.py`, `run_lab.py`).
- Artefactos: `summary.json`, `sample_manifest.csv` y `samples/`. Las 200 máscaras no se guardan; se regeneran de forma determinista.

## Principio aplicado

`generate_mask(image, method, parameters)` no tiene argumento de clase. Las tres funciones reciben solo píxeles y parámetros globales. La clase del manifiesto se lee **después** de generar todas las máscaras, solo para estadísticas agregadas, rótulos de paneles y el control de fuga. Ningún parámetro se eligió con métricas de clasificación.

## A. Métodos implementados

| Método | Versión | Procedimiento |
|---|---|---|
| `otsu_intensity` | 1 | RGB → luminancia → Gaussian σ=1 → Otsu sobre toda la imagen → foreground = brillante → elimina objetos < 64 px → rellena huecos ≤ 64 px |
| `hsv_otsu` | 1 | Región celular (max(RGB) > 0,04, rellena, erosión de 3 px) → saturación HSV, σ=1 → **Otsu calculado solo sobre píxeles celulares** → elimina objetos < 16 px |
| `stain_morph` | 2 | Región celular (igual) → saturación HSV, σ=1 → foreground = S > **mediana(S de la propia célula) + 0,15** → `remove_small_objects` (< 20 px) → `remove_small_holes` (≤ 30 px) → apertura y cierre con disco r=1 |

Implementación: `u1b-lab-1`, con scikit-image 0.26, numpy y PIL. Sin OpenCV.

**`stain_morph` v1 descartado.** La v1 usaba el canal hematoxilina de `rgb2hed` con delta 0,03. Ese canal tiene un rango muy pequeño, y la v1 dejaba vacías el 86 % de las máscaras parasitadas aun con focos violeta evidentes (AUC geométrica 0,55). Fue un error de escala, no un efecto de clase.

La v2 cambia a saturación. El delta 0,15 se tomó del **valle de la distribución agrupada y sin label** del contraste por célula (p99,5 − mediana de S) sobre la muestra. Esa distribución es bimodal: un modo en ≈ 0,02–0,06 y otro en ≈ 0,3–0,5.

## B. Muestra

- 200 imágenes TRAIN: 100 parasitized y 100 uninfected, de **100 pacientes**.
- Orden determinista `md5('u1b-2026-10-02' || source_record_id)`. La clase solo se usa para estratificar la muestra.
- Cada fila registra `source_record_id`, `source_filename`, `patient`, `split`, `class` y `relative_path`.
- Reproducibilidad verificada: al regenerarlos, el manifiesto y `summary.json` son idénticos byte a byte.

## C. Resultados cuantitativos

Las estadísticas se calculan a resolución nativa. `fg` es la fracción de foreground sobre la imagen completa; `cc` son las componentes conexas (conectividad 8).

| Método | Clase | fg mediana | fg p10–p90 | Vacías | Llenas | cc media | Mayor comp. (mediana) |
|---|---|---:|---|---:|---:|---:|---:|
| otsu_intensity | parasitized | 0,723 | 0,599–0,782 | 0 % | 0 % | 1,01 | 1,00 |
| otsu_intensity | uninfected | 0,739 | 0,622–0,780 | 0 % | 0 % | 1,01 | 1,00 |
| hsv_otsu | parasitized | 0,014 | 0,007–0,187 | 0 % | 0 % | 1,61 | 1,00 |
| hsv_otsu | uninfected | 0,401 | 0,095–0,558 | 0 % | 0 % | 2,90 | 1,00 |
| stain_morph v2 | parasitized | 0,012 | 0,005–0,026 | 4 % | 0 % | 1,44 | 1,00 |
| stain_morph v2 | uninfected | 0,000 | 0,000–0,000 | 94 % | 0 % | 0,07 | 0,00 |

**Estabilidad.** Se mide como el IoU mínimo frente a perturbar el parámetro principal: σ 0,5 y 1,5 para A y B; delta 0,12 y 0,18 (±20 %) para C.

| Método | IoU mediana | IoU p10 |
|---|---:|---:|
| otsu_intensity | 0,994 | 0,990 |
| hsv_otsu | 0,957 | 0,899 |
| stain_morph v2 | 0,920 | 0,721 |

En C, el p10 bajo viene de células en el umbral, cuya máscara pasa de vacía a no vacía (IoU = 0).

**Control de fuga.** Se entrena una regresión logística sobre `foreground_fraction`, `connected_components` y `largest_component_fraction`, con 5 folds agrupados por paciente, y se reporta el ROC-AUC out-of-fold.

| Entrada | AUC |
|---|---:|
| Geometría de `otsu_intensity` | 0,544 |
| Geometría de `hsv_otsu` | 0,899 |
| Geometría de `stain_morph` v2 | 0,932 |
| **Referencia sin máscara:** 2 estadísticos de color de la imagen (p1 de gris y p99 de saturación de la célula) | 0,902 |

## D. Resultados visuales (`samples/`)

- `panel_<método>.png`: RGB | MASK | OVERLAY | MASKED RGB a 200×200. La imagen se reescala con bilinear, como en el pipeline; la máscara con **nearest** y se mantiene `bool`. Incluye 4 células de cada clase.
- `compare_methods.png`: las mismas 8 células, con un overlay por método.
- `edge_cases_stain_morph.png`: parasitized con máscara vacía y uninfected con máscara no vacía (auditoría). Los paneles equivalentes de A y B no se versionan: esos métodos nunca producen máscaras vacías, así que solo repiten ejemplos uninfected.

## E. Análisis por clase

- **otsu_intensity.** Sin diferencia por clase (fg ≈ 0,72 frente a 0,74; AUC 0,54). No hay degeneración ni fuga.
- **hsv_otsu.** Degeneración **invertida**. Otsu siempre encuentra un umbral, así que en células homogéneas (casi todas las uninfected) parte la célula en dos y segmenta el anillo periférico frente a la palidez central (fg ≈ 40 %). Cuando existe un foco denso, lo aísla (fg ≈ 1 %). El área de la máscara termina codificando "¿hay foco o no?" por la vía de un artefacto del umbral adaptativo. No hay máscaras vacías en ninguna clase.
- **stain_morph v2.** Es la configuración "parasitized → foreground, uninfected → vacía" en el 94 % y 96 % de los casos. La regla **no** usa la clase, y los casos límite muestran que sigue a la tinción:
  - 4 parasitized vacías: inclusiones pegadas al borde que la erosión de 3 px elimina, o sin tinción visible (posible ruido de etiquetado del dataset NIH).
  - 6 uninfected no vacías: restos de tinción, solapamiento con otra célula y una inclusión que parece real.

  Aun así, la máscara es casi un detector binario de la clase. Su geometría alcanza AUC 0,93, cerca de lo que logran 2 estadísticos de color de la imagen cruda (0,90). La máscara no agrega información de clase que no esté ya en la imagen, pero la **hace explícita y espacial**.

## F. Interpretación (sin ground truth)

| Método | Foreground razonable | Vacías | Artefactos | Hard Attention viable | Qué segmenta |
|---|---|---:|---|---|---|
| Otsu intensity | Sí, como silueta celular | 0 % | Ninguno relevante; conserva los focos (mediana 100 % del foco dentro de la máscara) | Técnicamente sí, pero es **casi la identidad**: descarta una mediana de 0,1 % de los píxeles celulares, porque el fondo ya es negro | **Eritrocito completo** frente al fondo de padding |
| HSV (Otsu adaptativo) | Solo cuando hay foco | 0 % | Anillo periférico o mitades arbitrarias en células homogéneas | No: en células sin foco entrega a DenseNet regiones arbitrarias | **Región de mayor saturación relativa**: foco denso si existe, si no el anillo periférico |
| Color + morfología | Sí, para focos de tinción | 4 % / 94 % | Pierde inclusiones de borde (erosión); capta restos de tinción | Funciona, pero **apaga casi toda célula uninfected**: DenseNet recibiría imágenes negras y la decisión la tomaría la máscara | **Focos de tinción intensa** (alta saturación focal): posibles estructuras parasitarias, pero también restos y solapamientos |

Ningún método segmenta "el parásito" en un sentido verificable: no hay ground truth. Los nombres correctos son *silueta celular* (A), *región de saturación relativa* (B) y *focos de tinción intensa* (C).

## G. Método candidato

**`stain_morph` v2.** Razones:

- Es simple: un umbral fijo relativo a la propia célula y morfología estándar.
- Es interpretable ("foco de tinción intensa") y tiene la mejor calidad visual en focos.
- No tiene fuga explícita: la regla es ciega a la clase, y existen excepciones en ambos sentidos.
- Es el único de los tres que puede decir "no hay estructura" sin inventar una región.
- Es razonablemente estable (IoU mediana 0,92).

Condiciones que deben acompañarlo:

1. **Multi-Task.** La máscara es una pseudo-etiqueta de *focos de tinción*. Su cabeza de segmentación será casi redundante con la clasificación. El experimento sigue siendo válido, porque la máscara no es input y deriva de la imagen, pero el resultado debe leerse como "supervisión espacial de focos", no como "segmentación de parásitos".
2. **Hard Attention.** Con esta máscara, la U-Net decide de hecho qué ve DenseNet, y una célula sin foco llega en negro. Antes de entrenar hay que decidir si se acepta así o si se agrega un **control** con `otsu_intensity`. Ese control es casi la identidad y sirve como línea base de "enmascarar sin quitar información".
3. Hay que reportar Dice/IoU como acuerdo con la pseudo-máscara, nunca como exactitud de segmentación.

## H. Parámetros candidatos

```json
{
  "method_name": "stain_morph",
  "method_version": 2,
  "implementation_version": "u1b-lab-1",
  "parameters": {
    "color_transform": "hsv_saturation",
    "blur_sigma": 1.0,
    "background_max_value": 0.04,
    "cell_erosion_radius": 3,
    "stain_delta": 0.15,
    "min_object_px": 20,
    "max_hole_px": 30,
    "opening_radius": 1
  },
  "resize": "nearest",
  "dtype_generation": "bool"
}
```

## I. Limitaciones

- **pseudo-mask ≠ ground truth.** No hay anotación experta; ninguna métrica mide si se segmenta un parásito.
- `stain_delta = 0,15` sale de la distribución de esta muestra de 200 imágenes. Antes de la generación gobernada conviene confirmar el valle en un subconjunto TRAIN disjunto, también sin label.
- La erosión de 3 px elimina inclusiones pegadas al borde celular (4 de los casos vacíos).
- Los restos de tinción, plaquetas y solapamientos se segmentan igual que las inclusiones.
- La máscara de C es casi binaria por clase. Eso proviene del dataset (las etiquetas NIH dependen de inclusiones visibles), no de la regla, pero limita lo que Multi-Task y Hard Attention pueden demostrar.
- La muestra es pequeña (200 imágenes, 100 pacientes). La variación de tinción entre pacientes puede requerir revisar el delta en la muestra mayor.
- El test de fuga usa solo geometría global, no la posición de la máscara.

## J. Decisión

**¿Existe al menos un método suficientemente razonable para avanzar a generación gobernada de pseudo-máscaras? SÍ**, con `stain_morph` v2 y bajo las condiciones de G. Antes de generar el dataset completo:

- (a) Confirmar el valle del delta en otro subconjunto TRAIN, sin usar labels.
- (b) Decidir explícitamente cómo se interpretará Hard Attention cuando la máscara esté vacía.

## Reproducir

```bash
# Desde scripts/experiments/unet_masks/, con el venv .venv-local-train
U1B_DATABASE_URL=postgresql+psycopg://USER:PASS@127.0.0.1:5432/malaria_experiments \
  python sample.py --data-root <malaria_dl_local_project/data/malaria_dataset_versions/d8c0...> \
                   --out results/u1b/sample_manifest.csv
python run_lab.py --data-root <...d8c0...> --manifest results/u1b/sample_manifest.csv --out results/u1b
```
