# U1B.1 — Validación independiente y congelación de `stain_morph` v2

- Dataset: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, solo **TRAIN**.
- Rama `exp/u1b-pseudo-masks`. U1B quedó preservado en el commit `49f8618`.
- No se tocó VAL ni TEST, PostgreSQL (solo lectura), los loaders, la campaña ni `main`.
- Código: `sample_validation.py` (muestra) y `validate.py` (fase ciega → congelación → auditoría).

## Evolución y decisiones registradas

```
U1B   (commit 49f8618)   delta candidato = 0.15   (evidencia en results/u1b/, no se reescribe)
        ↓ validación independiente: otra muestra TRAIN, otros pacientes, regla pre-registrada sin labels
U1B.1                    delta congelado = 0.20   (este informe)
```

- **Generador congelado:** `stain_morph` v2, `stain_delta = 0.20`, entry point `masks.generate_frozen_pseudo_mask(image)`. Genera `mask = f(image)` y nunca accede a la etiqueta. Los defaults de `METHODS` en `masks.py` conservan los valores de U1B (0.15), así que U1B se sigue reproduciendo byte a byte. La configuración congelada es una constante separada (`FROZEN_PSEUDO_MASK`).
- **Limitación registrada:** la pseudo-máscara derivada de tinción está fuertemente correlacionada con la clase (AUC geométrica 0,91). El generador **no recibe, no consulta y no deriva directamente** la etiqueta, por lo que **no se describe como fuga de etiqueta**. La correlación es una limitación experimental y puede reflejar la señal cromática presente en el dataset.
- **Decisión Hard Attention:** máscara *predicha* vacía → masked RGB completamente negro (opción A, sección H). No implementado todavía.
- **Control:** `otsu_intensity` v1 se conserva como control experimental (sección I).

## Diseño en dos fases

1. **Fase ciega.** Usa solo píxeles. `validate.py` construye los registros sin columna de clase y calcula:
   - la distribución de contraste;
   - el valle por KDE;
   - el barrido de delta;
   - la regla de selección pre-registrada;
   - la estabilidad;
   - la congelación: especificación y SHA-256 de `masks.py`. El script falla si la constante `FROZEN_PSEUDO_MASK` no coincide con la salida de la regla.
2. **Auditoría.** Solo después de congelar se abre `validation_labels.csv`, un archivo separado del manifiesto. Sus resultados no retroalimentan delta.

```
imagen → stain_morph → pseudo-máscara          (nunca: imagen + label → stain_morph)
```

Nota de honestidad: la materialización gobernada guarda cada archivo bajo el directorio de su clase, así que `relative_path` contiene el nombre de la clase. Ese path solo se usa para abrir el archivo. `generate_mask` recibe únicamente el arreglo de píxeles.

## A. Independencia de la muestra

| | Valor |
|---|---:|
| Imágenes | 200 (TRAIN) |
| Pacientes | 57 |
| Overlap de imágenes con U1B | **0** |
| Overlap de pacientes con U1B | **0** |

- Selección: `md5('u1b1-2026-10-02' || source_record_id)`, sin filtro ni estratificación por clase, excluyendo las imágenes y los pacientes de U1B.
- Composición resultante, conocida solo en la auditoría: **48 parasitized / 152 uninfected**. Los 61 pacientes de TRAIN que no estaban en U1B tienen más células no infectadas. No se rebalanceó, porque eso habría exigido usar la clase en la selección.

## B. Distribución de contraste (`samples/contrast_distribution.png`)

El contraste es p99,5 − mediana de la saturación HSV suavizada (σ=1) dentro de la célula erosionada, que es la misma región que usa el generador.

| Muestra | Modo bajo | Modo alto | Mínimo KDE (búsqueda en 0,05–0,30) | Densidad del valle / pico bajo | Percentiles 10/25/50/75/90 |
|---|---:|---:|---:|---:|---|
| U1B | 0,033 | 0,399 | **0,201** | 0,24 | 0,017 / 0,026 / 0,110 / 0,393 / 0,466 |
| U1B.1 | 0,033 | 0,442 | **0,254** | 0,05 | 0,014 / 0,021 / 0,034 / 0,085 / 0,433 |

**¿El valle vuelve a aparecer aproximadamente en la misma región? SÍ.** Ambas muestras son bimodales, con modos casi idénticos y una región de baja densidad entre ≈ 0,15 y 0,30.

El punto más profundo se desplaza (0,20 frente a 0,25), lo que es esperable: U1B.1 tiene menos células del modo alto y la KDE se aplana a la derecha. La afirmación de U1B de que el valle estaba en "≈ 0,12–0,17" venía de un histograma grueso. Con KDE, el mínimo en U1B está en 0,20.

## C. Delta

**Regla pre-registrada** (escrita en `validate.py` antes de ejecutar): elegir en `{0,10; 0,125; 0,15; 0,175; 0,20}` el delta con menor fracción de células ambiguas en U1B.1 (|contraste − delta| ≤ 0,025). En empate se mantiene 0,15.

Barrido en U1B.1, sin labels (`samples/delta_sweep.png`):

| delta | Máscaras vacías | Ambiguas U1B.1 | Ambiguas U1B | Cambios vacía↔no vacía frente a 0,15 | IoU mediana frente a 0,15 (células informativas) |
|---:|---:|---:|---:|---:|---:|
| 0,100 | 75,0 % | 5,5 % | 3,5 % | 3 | 0,68 |
| 0,125 | 75,5 % | 2,0 % | 2,0 % | 2 | 0,85 |
| 0,150 | 76,5 % | 2,0 % | 1,0 % | 0 | 1,00 |
| 0,175 | 78,0 % | 3,0 % | 1,0 % | 3 | 0,89 |
| **0,200** | 79,0 % | **1,5 %** | 2,0 % | 5 | 0,80 |

**Delta final = 0,20**, según la regla pre-registrada. Justificación sin labels:

- Es el valor del grid con menos células ambiguas en la muestra nueva.
- Coincide con el mínimo KDE de U1B (0,201) y queda por debajo del de U1B.1 (0,254), dentro de la región de baja densidad de ambas.

Limitación explícita: la regla discrimina poco. Entre 0,125 y 0,20, la diferencia es de 1 a 3 células de 200, y con ambas muestras juntas habría ganado 0,15. El intervalo 0,125–0,20 es una **meseta**: la tasa de vacías varía 3,5 puntos y solo 5 células cambian de estado entre 0,15 y 0,20. No se cambió la regla tras ver el resultado.

## D. Estabilidad: U1B frente a U1B.1, ambas con delta 0,20 y sin labels

| | U1B | U1B.1 |
|---|---:|---:|
| Máscaras vacías | 51,0 % | 79,0 % |
| Fracción de foreground, mediana (no vacías) | 0,0095 | 0,0094 |
| Componentes, media (no vacías) | 1,35 | 1,26 |
| Mayor componente, mediana (no vacías) | 1,00 | 1,00 |
| IoU mínima frente a delta ×0,8 / ×1,2: todas las células, mediana | 0,92 | 1,00 |
| Ídem, solo células informativas: n / mediana / p10 | 101 / 0,79 / 0,58 | 46 / 0,81 / 0,00 |

- **Cuando hay región, su forma es la misma en ambas muestras:** tamaño ≈ 0,9 % de la imagen, ≈ 1,3 componentes y una componente dominante.
- La tasa de vacías difiere por la composición de la muestra (ver E), no por el método.
- La IoU sobre todas las células está inflada por pares vacía-vacía. La IoU informativa (≈ 0,8) es la cifra honesta. Las regiones son pequeñas, así que unos pocos píxeles de borde mueven bastante la IoU. El p10 = 0 en U1B.1 corresponde a células que cambian de vacía a no vacía con ±20 % de delta.

## E. Auditoría posterior por clase (diagnóstico, no retroalimenta delta)

| Muestra (delta 0,20) | Clase | n | Vacías | fg mediana | fg p10–p90 | cc media | Mayor comp. |
|---|---|---:|---:|---:|---|---:|---:|
| U1B.1 | parasitized | 48 | 14,6 % | 0,0088 | 0,000–0,019 | 1,08 | 1,00 |
| U1B.1 | uninfected | 152 | 99,3 % | 0,000 | 0,000–0,000 | 0,01 | 0,00 |
| U1B | parasitized | 100 | 5,0 % | 0,0089 | 0,004–0,018 | 1,29 | 1,00 |
| U1B | uninfected | 100 | 97,0 % | 0,000 | 0,000–0,000 | 0,03 | 0,00 |

Con la composición de U1B.1 (24 % parasitized), las tasas por clase de U1B predicen ≈ 75 % de vacías globales, cerca del 79 % observado. Las parasitized de U1B.1 tienen más vacías (14,6 % frente a 5 %): sus inclusiones son más tenues en esta muestra de pacientes (ver G).

## F. Geometría frente a label

Regresión logística sobre `foreground_fraction`, `connected_components` y `largest_component_fraction`, con `StratifiedGroupKFold(5)` por paciente y ROC-AUC out-of-fold.

| Entrada | U1B (delta 0,15) | U1B.1 (delta 0,20) |
|---|---:|---:|
| Geometría de `stain_morph` | 0,932 | **0,907** |
| Geometría de `otsu_intensity` (control) | 0,544 | 0,525 |
| Referencia sin máscara: 2 estadísticos de color de la imagen | 0,902 | 0,884 |

Interpretación: la geometría de la pseudo-máscara predice la clase casi tanto como dos estadísticos de color de la imagen cruda.

- El generador **nunca recibe la etiqueta**, así que esto **no es fuga de etiqueta**.
- Refleja una característica visual real del dataset: las células etiquetadas como parasitized suelen contener inclusiones de alta saturación.
- Se documenta como **limitación experimental**. La pseudo-máscara está fuertemente correlacionada con la clase. En Multi-Task la tarea de segmentación será parcialmente redundante con la clasificación, y en Hard Attention el segmentador concentra gran parte de la decisión.
- El generador no se ajustó para subir ni bajar esta cifra.

## G. Máscaras vacías

Frecuencia en U1B.1: 79 % global (153 / 200). Las causas se calculan desde los píxeles:

| Causa | parasitized | uninfected |
|---|---:|---:|
| Ningún píxel supera mediana + delta | 5 | 148 |
| Región supera el umbral pero la eliminan tamaño o morfología (< 20 px, apertura) | 2 | 3 |
| Tinción solo en el borde (eliminada por la erosión de 3 px) | 0 | 0 |

Causas visuales en `samples/edge_cases_stain_morph.png`:

- Las parasitized vacías tienen inclusiones **tenues** (rosadas o lilas, de baja saturación) o **muy pequeñas**.
- La única uninfected no vacía (C238NThinF) contiene un punto teñido compacto: un resto de tinción o una inclusión no anotada.

## H. Hard Attention: semántica de la máscara vacía

| Opción | Qué recibe DenseNet121 | Consecuencia científica |
|---|---|---|
| **A. Vacía → imagen negra** | Solo la región indicada por el segmentador; si no hay región, un tensor constante | Respeta literalmente "usa únicamente la región indicada por el segmentador". No introduce ramas. Para la mayoría de las células sanas, DenseNet ve un input constante y la decisión la toma de hecho el segmentador. Eso es exactamente lo que el experimento debe medir. |
| B. Vacía → imagen original | Dos distribuciones de input según el output del segmentador | Introduce una excepción condicionada a la máscara. "Imagen completa" pasa a ser una señal implícita de "el segmentador no vio tinción", fuertemente asociada a la clase. Además rompe el significado de Hard Attention. |
| C. Vacía → máscara fallback (por ejemplo, la célula completa) | Igual que B en la práctica: la célula completa ≈ imagen original | Mismos problemas que B, y suma una segunda definición de máscara. Mezcla los brazos del experimento con el control `otsu_intensity`. |

**Recomendación: opción A**, con tres obligaciones de reporte para que el resultado sea interpretable:

1. La tasa de máscaras *predichas* vacías por split.
2. Una línea base de **solo segmentador**: predecir parasitized si la máscara predicha no está vacía. Así se mide cuánto agrega DenseNet sobre la decisión de vacío o no vacío.
3. El brazo de control `otsu_intensity` (ver I).

La opción A no usa la etiqueta en ningún punto. Si hay una correlación, es visible y medible, no una regla oculta.

## I. Control

**`otsu_intensity` v1 queda conservado como control experimental**, no como candidato. En U1B.1:

- fg ≈ 0,73–0,75 en ambas clases;
- 0 % de máscaras vacías;
- AUC geométrica 0,525;
- conserva el 100 % (mediana) de los focos de `stain_morph`.

Permite comparar:

```
DenseNet121 original
  vs  otsu_intensity whole-cell attention → DenseNet121   (efecto de solo enmascarar)
  vs  stain_morph hard attention → DenseNet121            (efecto de concentrarse en tinción intensa)
```

## J. Terminología

Términos oficiales: **pseudo-máscara**, **pseudo-máscara derivada de tinción** (*stain-derived pseudo-mask*). No se usan "ground truth", "máscara real del parásito" ni "segmentación clínica validada": no disponemos de ellas.

Interpretación más defendible de `stain_morph`: *regiones de tinción cromáticamente intensa (alta saturación relativa a la propia célula), obtenidas mediante procesamiento determinista independiente de la etiqueta*. No se afirma que cada región sea un trofozoíto u otra estructura parasitaria.

Frase para la memoria y la defensa:

> "Las pseudo-máscaras derivadas de tinción delimitan regiones de tinción cromáticamente intensa en cada célula, obtenidas por un procedimiento determinista sobre la saturación HSV que nunca utiliza la etiqueta de clasificación; no constituyen anotaciones del parásito."

## K. Decisión final

**`stain_morph` v2 queda congelado como generador de pseudo-máscaras: SÍ.**

```
method_name:            stain_morph
method_version:         2
implementation_version: u1b-lab-1
delta:                  0.20
parameters:             {color_transform: hsv_saturation, blur_sigma: 1.0, background_max_value: 0.04,
                         cell_erosion_radius: 3, stain_delta: 0.20, min_object_px: 20,
                         max_hole_px: 30, opening_radius: 1}
mask dtype / resize:    bool durante la generación; nearest al tamaño del pipeline
entry point:            masks.generate_frozen_pseudo_mask(image)
implementation hash:    sha256(masks.py) = 65603c61c4925345d83ca305e5d097514679e54b1aea0159e63bfac7f9be24e9
spec hash:              sha256(canonical spec) = 4a84ad75d71dacf8f3d9c79d9de668ed57db176b09d2b265fd55c00ebbca078b
control:                otsu_intensity v1 (defaults)
```

Lo que queda demostrado, dentro del alcance de U1B.1:

> El procedimiento genera de manera reproducible una representación espacial de regiones de tinción intensa usando solo información de la imagen, sin usar la etiqueta de clasificación.

- **Reproducibilidad:** la muestra, `summary.json` y la ejecución completa son deterministas, y U1B sigue reproduciendo byte a byte su `summary.json` con el `masks.py` actual.
- **Estabilidad:** la forma de la región es la misma en dos muestras independientes por paciente.

## Reproducir

```bash
# Desde scripts/experiments/unet_masks/, con .venv-local-train
U1B_DATABASE_URL=postgresql+psycopg://USER:PASS@127.0.0.1:5432/malaria_experiments \
  python sample_validation.py --data-root <...d8c0...> --exclude results/u1b/sample_manifest.csv \
                              --out-dir results/u1b_validation
python validate.py --data-root <...d8c0...> --out results/u1b_validation
```
