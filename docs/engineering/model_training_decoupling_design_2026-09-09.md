# Diseño — Desacoplamiento y trazabilidad del flujo de entrenamiento

Fecha: 2026-09-09
Rama: `main` · HEAD `31348bf8`
Rol: arquitecto de software senior — pipelines de ML, Python, PostgreSQL 17
Estado: **DISEÑO — no implementación.** Requiere aprobación explícita del responsable
antes de pasar a código. No se ha tocado ningún archivo de producción.

Documento base (no se reduplica, se extiende):
[`docs/audits/training_coupling_map_2026-09-09.md`](../audits/training_coupling_map_2026-09-09.md)
(mapa de los 16 puntos) y
[`docs/engineering/model_training_pipeline.md`](model_training_pipeline.md) (H1–H10).
Subsistema `run` y su purga:
[`docs/operations/subsystem_data_purge.md`](../operations/subsystem_data_purge.md).

---

## 0. Alcance y no-alcance

### 0.1 Qué resuelve este diseño

| Objetivo | Origen | Cómo |
|---|---|---|
| Consolidar los **13 puntos accidentales** (P0, P1, P3, P4, P5, P7, P9, P11, P12, P13, P14, P15, P16) en una fuente de verdad por modelo | mapa §2.1 | **D1** — contrato `ModelSpec` autocontenido + registro por auto-discovery |
| Preservar los **3 puntos reales** (P6 despacho, P8 guard densenet↔vgg16_imagenet, P13b vgg necesita caffe) sin diluirlos | mapa §2.1 | **D1** — se expresan como *datos declarados por el propio modelo*, no como ramas `if` que conocen a los demás |
| Cerrar la brecha del hallazgo 0.4: topología/hiperparámetros resueltos hoy solo reconstruibles vía `git checkout` | mapa §0.5, §4.2, §5.1-T5 | **D2** — `run_configuration_snapshots`: snapshot de la config **ya resuelta** de cada corrida, capturado antes de `fit()` |
| Poblar `environment_packages` (0 filas hoy) | mapa §5.1-T4 | **D2.3** — extensión barata del mismo mecanismo, `pip freeze` real en el momento de la corrida |
| Descubrimiento dinámico del orquestador (agregar modelo = crear archivo) | mapa §0.6, H1/H2 | **D3** — `run_train_all_models.py` lee el catálogo poblado por D1 |

### 0.2 Qué NO toca este diseño (decisión del responsable, mapa §0.3, prompt §3)

- **La definición de cada modelo sigue viviendo en Python, autocontenida en su módulo.**
  Esto es intencional (fine-tuning específico, callbacks propios, preprocesamiento
  horneado). El contrato de D1 **no** obliga a un esquema genérico de red; obliga a
  *exponer metadatos descubribles* junto a la red.
- **El flujo TRAIN→EVALUATE/EXPLAIN y el linaje `run_lineage`.** BD ya registra
  parámetros de ejecución, tiempo y el vínculo padre→hijo correctamente
  (`model_training_pipeline.md` §1.5). El snapshot de D2 es **información adicional**,
  nunca un reemplazo (ver §D2.4).
- **La gobernanza de versiones** (`model_versions.status`, `release_status`, stage-2).
- **El esquema de `dataset_versions` / `freeze_contract`.**

### 0.3 Qué queda explícitamente fuera, para una fase posterior

- **H3** — validación de `--dataset-version-id` en el orquestador antes de lanzar
  (ver §D3.2).
- **H4** — transacción/reanudación de lote (ver §D3.2). D2 introduce el `batch_id` que
  es **prerrequisito** de una reanudación futura, pero no la implementa.
- **H5** — dedupe físico de la fila huérfana `models.name='vgg16'`. D1 la neutraliza
  (deja de escribirse) pero no la borra; eso es limpieza de datos aparte (ver §D1.5).
- **T7** — registro de modelos *intentados* vs *completados* vs *excluidos*.
- Retrofit de trazabilidad completa a los 12 runs históricos de `92e36c72` (mapa §0.5:
  siguen auditables vía `git checkout`; no se pierde nada — ver §D1.6).

---

## D1 — Contrato del módulo autocontenido por modelo

### D1.1 Principio

Hoy el conocimiento "qué es este modelo y qué necesita" está repartido en 6 archivos
(mapa §1.3). El contrato lo concentra en **un módulo por modelo** que expone **un objeto
`ModelSpec`**. Todo consumidor (orquestador, `src.train`, tracking, EVALUATE/EXPLAIN)
lee de ahí, nunca reimplementa.

Separación clave para no romper la restricción del responsable:

| Capa | Vive en | Mutable entre corridas | Ejemplo |
|---|---|---|---|
| **Definición de la red** | función Python en `architectures.py` (o en el propio módulo del modelo) | sí, libremente | `build_custom_cnn`, capas, `Dropout(0.4)`, callbacks propios |
| **Metadatos declarados** (`ModelSpec`) | módulo del modelo, dato estático | sí, es código | `supports_fine_tuning=False`, `preprocessing.recommended="vgg16_imagenet"` |
| **Config resuelta de una corrida** | BD, **inmutable** una vez escrita | no | `run_configuration_snapshots` (D2) |

La red **no** se saca de Python. El `ModelSpec` es *descripción*, no *reemplazo* del
builder.

### D1.2 Interfaz exacta que cada módulo debe implementar

Ubicación propuesta: `src/malaria_dl/models/catalog/<name>.py`, un archivo por modelo.

> **EJEMPLO ILUSTRATIVO — no es implementación.** Define la forma del contrato para que
> el responsable lo evalúe.

```python
# src/malaria_dl/models/spec.py  (infra del contrato, EJEMPLO)
from dataclasses import dataclass, field
from typing import Callable, Literal
import importlib

PreprocessingMode = Literal["rescale_0_1", "vgg16_imagenet"]

@dataclass(frozen=True, slots=True)
class PreprocessingContract:
    # P13/P13b: modo que el pipeline aplica en --preprocessing auto si no se fuerza otro
    default: PreprocessingMode = "rescale_0_1"
    # P13b: modo que la familia de arquitecturas REQUIERE para no degradar (vgg16 caffe)
    recommended: PreprocessingMode = "rescale_0_1"
    # P8: modos físicamente incompatibles con esta arquitectura
    incompatible: frozenset[str] = frozenset()
    # P9: la arquitectura hornea su propia normalización en el grafo (densenet)
    bakes_internal_normalization: bool = False
    internal_normalization_id: str | None = None   # p.ej. "densenet_imagenet_channel_mean_std"

@dataclass(frozen=True, slots=True)
class HyperparameterSpace:
    # valores por defecto YA concretos (no rangos) con los que corre si no se sobreescribe
    defaults: dict = field(default_factory=dict)
    # espacio de tuning declarado (informativo para D2 y para futuros barridos)
    search_space: dict = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class ModelSpec:
    # ---- identidad (única fuente de verdad) : mata P1, P4, P11, P12 ----
    name: str                              # nombre canónico en models.name
    cli_aliases: tuple[str, ...] = ()       # p.ej. ("vgg16",) para vgg16_transfer_learning
    path_aliases: tuple[str, ...] = ()      # segmentos de checkpoint históricos aceptables

    # ---- construcción : mata la mitad accidental de P6 y P10 ----
    builder_ref: str = ""                  # "src.malaria_dl.models.architectures:build_custom_cnn"
    returns_base_model: bool = False        # normaliza la arity (ver D1.2.1)

    # ---- capacidades declaradas como DATO, no como rama : mata P2, P7 ----
    supports_fine_tuning: bool = False
    pretrained_source: str | None = None    # "imagenet" | None
    fine_tune_unfreeze_layers: int | None = None   # P10: hoy política uniforme = 4

    # ---- preprocesamiento : preserva P8, P13b como dato descubrible ----
    preprocessing: PreprocessingContract = field(default_factory=PreprocessingContract)

    # ---- política de épocas : mata P5 ----
    recommended_max_epochs: int = 30

    # ---- optimizers compatibles : referencia, no reimplementa P0/P3/P16 ----
    compatible_optimizers: tuple[str, ...] = ("adam", "adamw", "sgd", "adadelta")

    # ---- hiperparámetros ----
    hyperparameters: HyperparameterSpace = field(default_factory=HyperparameterSpace)

    # ---- metadatos de catálogo (gobernanza) : mata P14 ----
    catalog_metadata: dict = field(default_factory=dict)
    # {"model_type": "...", "framework": "tensorflow/keras", "architecture": "...",
    #  "pretrained": bool, "pretrained_source": "imagenet"|None}

    # ---- versión del contenido del spec, para el snapshot D2 ----
    spec_version: str = "1"   # bump manual cuando cambian defaults/topología semántica

    def load_builder(self) -> Callable:
        module_path, _, attr = self.builder_ref.partition(":")
        return getattr(importlib.import_module(module_path), attr)
```

**Mínimo que cada archivo debe exponer:** exactamente un `ModelSpec` decorado con
`@register_model`. Nada más es obligatorio. El builder puede seguir en
`architectures.py` (se referencia por string, import perezoso) o vivir en el mismo
archivo del modelo si el autor prefiere tenerlo todo junto — el contrato no lo fuerza.

#### D1.2.1 Normalización de la arity de retorno (P6, P10)

Hoy `custom_cnn` devuelve `model` y los backbones devuelven `(model, base_model)`; la
diferencia se infiere por posición y se usa como señal implícita para el fine-tune
(mapa §1.2, "arity depende del modelo"). El contrato la vuelve **explícita**:

- `ModelSpec.returns_base_model: bool` declara la forma.
- Un adaptador único (`build_from_spec(spec, **kw) -> BuildResult(model, base_model|None)`)
  llama al builder y normaliza. Los builders **no cambian de firma** (crítico para el
  replay histórico, mapa §4.3).
- El dispatch de fine-tune deja de ser `if base_model is not None` (frágil) y pasa a ser
  `if spec.supports_fine_tuning and ft_epochs > 0`.

### D1.3 Mecanismo de registro — evaluación de las 3 opciones

Criterio: cómo queda cada una frente a los **3 puntos de acoplamiento real**.

| Criterio | (a) Decorador `@register_model` + auto-discovery de `catalog/` | (b) Convención de nombre de archivo + descubrimiento | (c) `MODEL_REGISTRY` explícito editado a mano |
|---|---|---|---|
| **P6 — despacho nombre→constructor sin duplicar** | ✅ el `name` del spec es la clave; `spec.builder_ref` el valor. Cero repetición. | ✅ igual, pero el nombre canónico queda atado al filename (frágil si se renombra el archivo) | ⚠️ funciona, pero requiere editar `registry.py` **además** de crear el archivo → sigue habiendo 2 sitios (el problema H1/H2 de origen) |
| **P8 — guard densenet↔vgg16_imagenet sin que un modelo sepa de otro** | ✅ densenet declara `preprocessing.incompatible={"vgg16_imagenet"}` en su propio spec; el resolver genérico lo aplica. Ningún modelo referencia a otro. | ✅ idem | ✅ idem (el guard no depende del mecanismo de registro) |
| **P13b — vgg declara que necesita caffe, descubrible** | ✅ `preprocessing.recommended="vgg16_imagenet"` en `catalog/vgg16_transfer_learning.py`. El substring-match `"vgg16" in name` de `preprocessing.py:42` desaparece. | ✅ idem | ✅ idem |
| **Agregar modelo = 1 archivo, 0 ediciones externas** | ✅ | ✅ | ❌ (edita `registry.py`) |
| **Falla ruidosa ante nombre desconocido** | ✅ `resolve_spec(name)` levanta `UnknownModelError` con la lista registrada | ✅ | ✅ |
| **Import barato para el orquestador (sin TF al listar)** | ✅ los módulos `catalog/*` importan solo `spec.py` (stdlib+dataclasses); el builder es import perezoso vía `builder_ref` | ✅ si se respeta la misma disciplina | ✅ si `registry.py` no importa `architectures.py` directo (hoy **sí** lo hace → habría que invertirlo) |
| **Orden de importación / import implícito** | ⚠️ el auto-discovery hace `pkgutil.iter_modules` sobre el paquete; hay que garantizar que se ejecuta una vez (en `models/__init__.py` o primera llamada a `resolve_spec`) | ⚠️ igual | ✅ trivial (import normal) |
| **Descubrimiento en tests / editable installs** | ✅ `pkgutil` sobre el paquete instalado funciona en editable | ✅ | ✅ |

**Recomendación: (a) decorador + auto-discovery.**
Razón: es la única que cumple "agregar modelo = crear su archivo, sin tocar nada más"
(objetivo explícito de D3.1) y a la vez mantiene el nombre canónico como dato dentro del
archivo (no atado al filename, como en (b)). Los 3 puntos reales quedan expresados como
**datos que el propio modelo declara sobre sí mismo**, nunca como conocimiento cruzado.

> **EJEMPLO ILUSTRATIVO — registro y resolución**

```python
# src/malaria_dl/models/registry.py  (EJEMPLO — reemplaza el código muerto actual)
import pkgutil, importlib
from .spec import ModelSpec

_CATALOG: dict[str, ModelSpec] = {}
_DISCOVERED = False

class UnknownModelError(KeyError): ...

def register_model(spec: ModelSpec) -> ModelSpec:
    if spec.name in _CATALOG:
        raise ValueError(f"Modelo '{spec.name}' registrado dos veces")
    for alias in (*spec.cli_aliases, *spec.path_aliases):
        # aliases no pueden colisionar con un nombre canónico de otro modelo
        ...
    _CATALOG[spec.name] = spec
    return spec

def _discover() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return
    from . import catalog
    for mod in pkgutil.iter_modules(catalog.__path__):
        importlib.import_module(f"{catalog.__name__}.{mod.name}")
    _DISCOVERED = True

def iter_model_specs() -> list[ModelSpec]:
    _discover()
    return sorted(_CATALOG.values(), key=lambda s: s.name)

def resolve_spec(name_or_alias: str) -> ModelSpec:
    _discover()
    if name_or_alias in _CATALOG:
        return _CATALOG[name_or_alias]
    for spec in _CATALOG.values():
        if name_or_alias in spec.cli_aliases or name_or_alias in spec.path_aliases:
            return spec
    raise UnknownModelError(
        f"Modelo '{name_or_alias}' no registrado. Disponibles: {sorted(_CATALOG)}"
    )

# compat shim (una release): otras partes del código que aún importan MODEL_REGISTRY
def __getattr__(attr):
    if attr == "MODEL_REGISTRY":
        return {s.name: s.load_builder() for s in iter_model_specs()}
    raise AttributeError(attr)
```

```python
# src/malaria_dl/models/catalog/vgg16_transfer_learning.py  (EJEMPLO)
from ..spec import ModelSpec, PreprocessingContract, HyperparameterSpace
from ..registry import register_model

vgg16_transfer_learning = register_model(ModelSpec(
    name="vgg16_transfer_learning",
    cli_aliases=("vgg16",),                         # P11: alias declarado, no función parche
    path_aliases=("vgg16",),                        # P12
    builder_ref="src.malaria_dl.models.architectures:build_vgg16_transfer",
    returns_base_model=True,
    supports_fine_tuning=True,                      # P7 como dato
    pretrained_source="imagenet",                   # P2 como dato
    fine_tune_unfreeze_layers=4,                    # P10: política uniforme, explícita
    preprocessing=PreprocessingContract(
        default="rescale_0_1",                      # lo que corre hoy en --preprocessing auto
        recommended="vgg16_imagenet",              # P13b: la familia vgg REQUIERE caffe
    ),
    recommended_max_epochs=30,                      # P5
    hyperparameters=HyperparameterSpace(
        defaults={"dense_units": 1024, "dropout_rate": 0.5, "l2_weight": 0.0},
        search_space={"dropout_rate": [0.3, 0.5], "dense_units": [512, 1024]},
    ),
    catalog_metadata={                              # P14
        "model_type": "transfer_learning", "framework": "tensorflow/keras",
        "architecture": "VGG16 + custom binary head",
        "pretrained": True, "pretrained_source": "imagenet",
    },
    spec_version="1",
))
```

```python
# src/malaria_dl/models/catalog/densenet121.py  (EJEMPLO — el guard P8, sin conocer a vgg)
densenet121 = register_model(ModelSpec(
    name="densenet121",
    builder_ref="src.malaria_dl.models.architectures:build_densenet121_transfer",
    returns_base_model=True,
    supports_fine_tuning=True,
    pretrained_source="imagenet",
    fine_tune_unfreeze_layers=4,
    preprocessing=PreprocessingContract(
        default="rescale_0_1",
        recommended="rescale_0_1",
        incompatible=frozenset({"vgg16_imagenet"}),   # P8: doble normalización → prohibido
        bakes_internal_normalization=True,            # P9: dato, no cadena derivada por if
        internal_normalization_id="densenet_imagenet_channel_mean_std",
    ),
    recommended_max_epochs=30,
    catalog_metadata={
        "model_type": "transfer_learning", "framework": "tensorflow/keras",
        "architecture": "DenseNet121 + global average pooling + binary head",
        "pretrained": True, "pretrained_source": "imagenet",
    },
    spec_version="1",
))
```

#### D1.3.1 Dónde vive cada punto real tras el refactor

| Punto real | Antes | Después |
|---|---|---|
| **P6** despacho nombre→constructor | `if/elif/else` en `trainer.py:1472-1492` (else = densenet en silencio) | `resolve_spec(name).load_builder()` — dict lookup, `UnknownModelError` si falta |
| **P8** guard densenet↔vgg16_imagenet | `if args.model=="densenet121" and preprocessing=="vgg16_imagenet"` en `parse_args` | resolver genérico: `if requested in spec.preprocessing.incompatible: raise`. densenet lo declara en **su** archivo. |
| **P13b** vgg necesita caffe | `"vgg16" in name.lower()` en `preprocessing.py:42` | `spec.preprocessing.recommended`. El resolver compara `recommended` vs `effective` y lo registra (cierra T6). |

El resolver de preprocesamiento pasa de recibir `model_name: str` (parámetro inerte,
P13) a recibir `spec: ModelSpec`:

```python
# EJEMPLO
def resolve_preprocessing_mode(spec: ModelSpec, requested: str = "auto") -> ResolvedPreprocessing:
    if requested != "auto" and requested in spec.preprocessing.incompatible:
        raise IncompatiblePreprocessingError(spec.name, requested)   # P8 genérico
    effective = spec.preprocessing.default if requested == "auto" else requested
    return ResolvedPreprocessing(
        effective=effective,
        recommended=spec.preprocessing.recommended,
        is_deviation=(effective != spec.preprocessing.recommended),   # T6: queda registrable
    )
```

### D1.4 Consolidación de los 13 puntos accidentales

| Punto | Hoy | Tras D1 |
|---|---|---|
| P0 `DEFAULT_OPTIMIZERS` | lista en orquestador | `sorted({o for s in iter_model_specs() for o in s.compatible_optimizers})` — o se deja como config **de grilla** (no de modelo); ver D3 |
| P1 `DEFAULT_MODELS` + choices | lista literal | `[s.name for s in iter_model_specs()]` |
| P3 `optimizer_learning_rates()` | cadena de `if` en orquestador | **no es dato por-modelo** → config de grilla (`grid_defaults.py` o tabla de política), fuera del `ModelSpec`. Se mantiene en un solo lugar. |
| P4 `--model choices` en `trainer.py` | lista literal | `choices=[s.name for s in iter_model_specs()]` |
| P5 `DEFAULT_MAX_EPOCHS_BY_MODEL` (muerto) | dict, `KeyError` si falta | `spec.recommended_max_epochs` (con default en el dataclass → nunca `KeyError`) |
| P7 guard fine-tune custom_cnn | `if model=="custom_cnn"` | `if ft_epochs>0 and not spec.supports_fine_tuning: raise` |
| P9 `model_internal_preprocessing` | `"..." if model=="densenet121" else None` | `spec.preprocessing.internal_normalization_id` |
| P11 `model_name_from_train_arg` | función parche `vgg16→vgg16_transfer_learning` | `resolve_spec(cli_arg).name`; la función queda como wrapper de 1 línea sobre el registry |
| P12 `model_name_from_checkpoint` | 6 nombres hardcodeados | `resolve_spec(segment).name` probando `path_aliases`; nombres no-entrenables (`ensemble`, `svm`, `tta`) se registran como specs "no entrenables" o se dejan en una lista aparte declarada |
| P13 `resolve_preprocessing_mode(model_name,...)` param inerte | recibe string no usado | recibe `spec`, lo usa (ver D1.3.1) |
| P14 `model_defaults` | dict en `tracking.py` | `spec.catalog_metadata`; `tracking.get_or_create_model` lo lee del spec. Fallback `unknown` → **error** (falla ruidosa) |
| P15 `MODEL_REGISTRY` muerto | dict `name→callable` aislado | `_CATALOG` vivo, poblado por auto-discovery; el símbolo `MODEL_REGISTRY` queda como shim compat una release |
| P16 `build_optimizer` (`momentum=0.9`) | despacho por-optimizer + literal | sin cambio estructural (es config de optimizer, no de modelo); **pero** el valor resuelto queda capturado por D2 (`optimizer.get_config()`) — cierra T5 para `momentum` |

**Lo que MIXTO (P2, P10) resuelve:** el *hecho* ("tiene backbone", "se fine-tunea")
pasa a `supports_fine_tuning` / `pretrained_source` (dato por-arquitectura). El *valor de
política uniforme* (`ft_epochs=20`, `n_layers=4`) se declara explícito en el spec con su
valor actual, pero queda claro en el trade-off (§T&O-2) que es política, no propiedad
intrínseca — un futuro barrido podría moverlo a config de grilla sin tocar el contrato.

### D1.5 Plan de migración de los 3 modelos existentes

Migración en **4 PRs pequeños, cada uno verde en CI antes del siguiente**. Sin big-bang.

**PR-1 — Infra del contrato (sin conectar nada).**
- Crear `models/spec.py` (`ModelSpec`, `PreprocessingContract`, `HyperparameterSpace`).
- Reescribir `models/registry.py`: `_CATALOG`, `register_model`, `_discover`,
  `iter_model_specs`, `resolve_spec`, `UnknownModelError`, shim `MODEL_REGISTRY`.
- Crear `models/catalog/__init__.py` + los 3 archivos:
  `custom_cnn.py`, `vgg16_transfer_learning.py`, `densenet121.py`.
  Los builders **no se tocan** — se referencian por `builder_ref`.
- Tests: `test_model_catalog.py` — cada spec resuelve su builder; `iter_model_specs()`
  devuelve 3; `resolve_spec("vgg16").name == "vgg16_transfer_learning"`;
  `resolve_spec("desconocido")` levanta `UnknownModelError`.
- **Nada en `trainer.py` / orquestador todavía.** `MODEL_REGISTRY` shim mantiene
  compatibilidad de imports.

**PR-2 — `src.train` consume el catálogo.**
- `parse_args`: `--model choices` desde `iter_model_specs()`; validación vía
  `resolve_spec` (falla ruidosa).
- Reemplazar el `if/elif/else` de `trainer.py:1472-1492` por
  `build_from_spec(resolve_spec(args.model), input_shape=..., learning_rate=..., optimizer_name=..., weights=...)`.
- Guards P7/P8 → genéricos leyendo el spec.
- `resolve_preprocessing_mode(spec, requested)`; propagar `ResolvedPreprocessing`.
- P5: `spec.recommended_max_epochs`.
- Tests: `test_train_integration.py` extendido — las 3 arquitecturas se construyen igual
  que antes (comparar `model.to_json()` contra golden de pre-refactor).

**PR-3 — `tracking.py` consume el catálogo.**
- `model_defaults` → `resolve_spec(name).catalog_metadata`; sin entrada → error.
- `model_name_from_train_arg` / `model_name_from_checkpoint` → wrappers sobre
  `resolve_spec`.
- Golden test: `get_or_create_model` produce los mismos campos que hoy para los 3.

**PR-4 — Orquestador (D3).** Ver §D3.

**Symbol shim retirado en PR-5** (release siguiente), tras confirmar 0 referencias a
`MODEL_REGISTRY` como dict.

### D1.6 Preservación de los 12 runs históricos de `92e36c72`

**Garantía:** los 12 `runs.command` / `execution_parameters->cli_arguments` siguen
siendo re-ejecutables contra `HEAD` **mientras** (a) las firmas de `build_custom_cnn` /
`build_vgg16_transfer` / `build_densenet121_transfer` **no cambien** — el diseño las
respeta — y (b) los tokens CLI `custom_cnn` / `vgg16` / `densenet121` sigan resolviendo.
`vgg16` resuelve por `cli_aliases`. El `else`-catch-all desaparece pero eso es una
mejora: un nombre viejo válido resuelve, uno inválido falla ruidoso (antes entrenaba
densenet en silencio).

**Sello v0.** En PR-1 se agrega `models/catalog/_v0_pre_decoupling.md` (no código):
tabla congelada de los valores implícitos que rigieron hasta el refactor
(`ft_epochs=20`, `n_layers=4`, `max_epochs=100` desde grilla, `momentum=0.9`,
`Dense(1024)/Dense(128)`, `Dropout` rates, `l2=1e-4`, `preprocessing=rescale_0_1` para
los 4 vgg16 pese a `recommended=vgg16_imagenet`). Es el "registro 0" que pide el mapa
§4.3. Reproducir un run < 2026-09-09 sigue siendo `git checkout 92e36c72` — **eso no
cambia y se documenta como contrato explícito** (mapa §6.3, pregunta 6).

**No se retrofitea** `run_configuration_snapshots` a runs pasados. Quedan sin fila de
snapshot; su `git_commit` + el sello v0 los cubre.

---

## D2 — Mecanismo de snapshot de configuración resuelta a BD

### D2.1 Estructura de datos: **tabla nueva `run_configuration_snapshots`** (1:1 con `runs`)

**Decisión: tabla nueva, no columna JSONB en `runs`.** Justificación contra el
subsistema `run` ya mapeado (`subsystem_data_purge.md`):

| Criterio | Columna `runs.configuration_snapshot JSONB` | **Tabla `run_configuration_snapshots`** |
|---|---|---|
| Guarda de cobertura de esquema de la purga (`subsystem_data_purge.md` §Guardas 2: "tabla nueva sin clasificar → aborta") | una columna nueva **pasa desapercibida** — riesgo de que datos de config queden sin gobernanza de purga explícita | ✅ fuerza actualizar `SUBSYSTEMS` en `purge.py` (`--run`: 28→29 tablas) — **el punto de control es intencional** |
| Escritura antes de `fit()` sin re-escribir `runs` | `UPDATE runs SET configuration_snapshot=...` compite con los `UPDATE runs` de `update_execution_tracking` (merge de JSONB, mapa §1.5-B) | ✅ `INSERT` independiente, una transacción propia, cero contención con el ciclo de vida de `runs` |
| Peso de la fila `runs` (ya ~40 columnas) | crece con un JSONB potencialmente grande (`model.to_json()` de densenet ≈ decenas de KB) | ✅ aislado; `runs` queda liviano para los `SELECT` de EVALUATE/EXPLAIN |
| Borrado en cascada bajo `--run` (`session_replication_role=replica`, delete explícito hijo→padre) | N/A (misma fila) | ✅ `run_id UUID REFERENCES runs(id) ON DELETE CASCADE`, orden topológico ya lo maneja `purge.py` |
| Consulta puntual "dame la config del run X" | `SELECT configuration_snapshot FROM runs WHERE id=X` | `SELECT * FROM run_configuration_snapshots WHERE run_id=X` — igual de simple |
| Evolución del esquema del snapshot | versionado solo dentro del JSON | `snapshot_schema_version` + posibilidad de columnas promovidas si se necesitan índices |

> **EJEMPLO ILUSTRATIVO — DDL propuesto (migración Alembic, `20260909_01`)**

```sql
CREATE TABLE run_configuration_snapshots (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id                  UUID NOT NULL UNIQUE REFERENCES runs(id) ON DELETE CASCADE,
    captured_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    capture_stage           TEXT NOT NULL DEFAULT 'pre_training',   -- futuro: 'pre_fine_tuning'
    snapshot_schema_version SMALLINT NOT NULL DEFAULT 1,

    -- identidad del módulo de modelo usado
    model_name              TEXT NOT NULL,
    model_spec_version      TEXT NOT NULL,          -- ModelSpec.spec_version
    model_spec_module       TEXT NOT NULL,          -- "src.malaria_dl.models.catalog.densenet121"
    source_fingerprint      JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- {"spec_module_sha256": "...", "architectures_sha256": "...", "builder_ref": "...:build_..."}

    -- CONFIG YA RESUELTA (el corazón del hallazgo 0.4)
    resolved_hyperparameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    resolved_topology        JSONB NOT NULL DEFAULT '{}'::jsonb,
    resolved_optimizer       JSONB NOT NULL DEFAULT '{}'::jsonb,
    resolved_preprocessing   JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- entorno / procedencia (cierra T2, T3, T4-resumen)
    environment              JSONB NOT NULL DEFAULT '{}'::jsonb,
    orchestration            JSONB NOT NULL DEFAULT '{}'::jsonb,

    metadata                 JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_run_config_snapshots_model
    ON run_configuration_snapshots (model_name, model_spec_version);
CREATE INDEX idx_run_config_snapshots_batch
    ON run_configuration_snapshots ((orchestration->>'batch_id'));
```

**Contenido de cada JSONB (valores YA RESUELTOS, no la definición general):**

| Campo | Qué captura | De dónde sale (confiable) | Cierra |
|---|---|---|---|
| `resolved_hyperparameters` | `learning_rate`, `fine_tune_learning_rate`, `fine_tune_epochs`, `max_epochs`, `batch_size`, `img_size`, `seed`, `optimizer`, `fine_tune_unfreeze_layers` (=4), `dropout_rate`, `dense_units`, `l2_weight`, `dropout_*` por capa | merge de: `args` resueltos en `trainer.main()` + `spec.hyperparameters.defaults` + kwargs efectivos pasados al builder | T5 (parcial), 0.4 |
| `resolved_topology` | `model.to_json()` del modelo **compilado y sin entrenar**, justo después de `build_from_spec` | Keras serializa el grafo exacto: cada `Dense(units)`, `Dropout(rate)`, la capa `Normalization` de densenet con sus mean/var, la pila conv de custom_cnn | 0.4, T5 (topología) |
| `resolved_optimizer` | `model.optimizer.get_config()` | Keras: `{"name":"SGD","learning_rate":0.001,"momentum":0.9,...}` — captura el `momentum=0.9` hardcodeado (P16) | T5 (`momentum`) |
| `resolved_preprocessing` | `{effective, recommended, is_deviation, internal_normalization_id}` | `ResolvedPreprocessing` de D1.3.1 | T6 |
| `environment` | `python_version`, `tensorflow_version`, `keras_version`, `numpy_version`, `cuda`/`cudnn` (`tf.sysconfig.get_build_info()`), `platform`, `machine`, `gpu_devices`, **`git_commit`, `git_dirty` (bool), `git_diff_stat`** | `collect_runtime_environment()` extendido con `git status --porcelain` + `git diff --stat` | T3, T4 (resumen) |
| `orchestration` | `batch_id` (UUID que genera el orquestador por invocación), `orchestrator_argv`, `orchestrator_version`, `grid_position` (`{model_index, optimizer_index}`), `requested_models`, `requested_optimizers` | pasado por el orquestador a `src.train` vía flags nuevos `--batch-id` / `--orchestrator-context` (JSON) | T1, T2 |
| `source_fingerprint` | sha256 del archivo del spec y de `architectures.py` en disco al momento de correr | `hashlib` sobre los `.py` | T3 (a nivel de archivo de modelo) |

`resolved_topology` vía `model.to_json()` es la decisión clave: **no obliga al autor del
modelo a mantener a mano una descripción de su red**. Se captura del objeto Keras ya
construido → siempre exacto, siempre completo, cero mantenimiento. La definición sigue en
Python; el snapshot es su fotografía resuelta.

### D2.2 Momento de captura y quién lo dispara

**Momento: dentro de `src.train` (`trainer.main()`), después de `build_from_spec()` +
`compile`, ANTES de `model.fit()`.**

```
trainer.main():
  args = parse_args()
  spec = resolve_spec(args.model)
  governed_dataset = resolve_governed_dataset(...)
  run_context = start_tracking_run(...)          # crea runs (status='started')  [YA EXISTE]
  ...
  model, base_model = build_from_spec(spec, ...) # construye + compila
  ├─► record_configuration_snapshot(             # <── NUEVO, punto único de captura
  │        run_context, spec, args, model,
  │        resolved_preprocessing, orchestration_context)
  ├─► log_environment_packages(run_context["run_id"])   # <── NUEVO (D2.3), mismo punto
  model.fit(...)                                  # si peta aquí, el snapshot YA está en BD
```

Por qué ahí:
- **Después de construir** el modelo → `model.to_json()` y `optimizer.get_config()`
  reflejan lo que *realmente* se va a entrenar (incluye defaults del builder que
  `args` no conoce).
- **Antes de `fit()`** → si el training muere a mitad (OOM, `kill -9`, error de datos),
  la fila de snapshot ya está confirmada. `runs.status` quedará `failed`/`started`
  huérfano, pero la config con la que se intentó **queda registrada** (requisito
  explícito del prompt §D2.2).
- Es **1 solo `INSERT`** en su propia transacción (vía `_execute_returning_id`, patrón
  existente en `run_repository.py`), idempotente por `run_id UNIQUE` (`ON CONFLICT DO
  NOTHING`).

**Quién dispara:**
- **El orquestador** genera el `batch_id` (una vez por invocación de
  `run_train_all_models.py`) y lo pasa a cada `src.train` como `--batch-id <uuid>` +
  `--orchestrator-context '<json>'`. **No escribe en BD** — sigue siendo stdlib pura
  (respeta `model_training_pipeline.md` §0.1). Solo aporta identidad de lote y sus
  propios argumentos como strings.
- **El módulo del modelo** NO escribe en BD ni conoce `run_context`. Solo expone el
  `ModelSpec` (dato). Mantenerlo DB-free es deliberado: un modelo es una definición, no
  un actor de persistencia.
- **`trainer.main()`** es el ensamblador: junta `spec` (del registry) + `args` resueltos
  + `model` construido + `orchestration_context` (de los flags) y llama a
  `record_configuration_snapshot`. Punto único, testeable.

> Corrida directa `python -m src.train ...` sin orquestador: `batch_id` se autogenera en
> `trainer.main()` y `orchestration.orchestrator_argv = sys.argv`; `grid_position` queda
> `null`. El snapshot se captura igual.

> **EJEMPLO ILUSTRATIVO — la función de captura**

```python
# src/malaria_dl/persistence/tracking.py  (EJEMPLO)
def record_configuration_snapshot(context, spec, args, compiled_model,
                                  resolved_preprocessing, orchestration_context):
    if not context or not context.get("run_id"):
        return None
    tracker = context["tracker"]
    payload = {
        "run_id": context["run_id"],
        "model_name": spec.name,
        "model_spec_version": spec.spec_version,
        "model_spec_module": type(spec).__module__ or spec_module_of(spec),
        "source_fingerprint": {
            "spec_module_sha256": sha256_of_module(spec),
            "architectures_sha256": sha256_of_file("src/malaria_dl/models/architectures.py"),
            "builder_ref": spec.builder_ref,
        },
        "resolved_hyperparameters": collect_resolved_hyperparameters(spec, args),
        "resolved_topology": json.loads(compiled_model.to_json()),
        "resolved_optimizer": compiled_model.optimizer.get_config(),
        "resolved_preprocessing": dataclasses.asdict(resolved_preprocessing),
        "environment": collect_runtime_environment_extended(),   # + git_dirty + diff_stat
        "orchestration": orchestration_context,
    }
    return tracker.safe_track(tracker.log_configuration_snapshot, **payload)
```

```python
# src/malaria_dl/persistence/run_repository.py  (EJEMPLO)
def log_configuration_snapshot(run_id, **fields):
    return _execute_returning_id(
        """
        INSERT INTO run_configuration_snapshots (
            run_id, model_name, model_spec_version, model_spec_module,
            source_fingerprint, resolved_hyperparameters, resolved_topology,
            resolved_optimizer, resolved_preprocessing, environment, orchestration
        ) VALUES (
            :run_id, :model_name, :model_spec_version, :model_spec_module,
            CAST(:source_fingerprint AS jsonb), CAST(:resolved_hyperparameters AS jsonb),
            CAST(:resolved_topology AS jsonb), CAST(:resolved_optimizer AS jsonb),
            CAST(:resolved_preprocessing AS jsonb), CAST(:environment AS jsonb),
            CAST(:orchestration AS jsonb)
        )
        ON CONFLICT (run_id) DO NOTHING
        RETURNING id
        """, {...})
```

### D2.3 Snapshot de `environment_packages`

**Reutiliza `log_environment_packages(run_id)` que YA EXISTE**
(`run_repository.py:1718`) y ya hace lo correcto: `importlib.metadata.distributions()` —
un freeze **real del entorno vivo**, no una lista estática. Hoy simplemente **nunca se
llama** en el flujo de training (mapa §5.1-T4, `model_training_pipeline.md` H).

Diseño:
- **Llamarla en el mismo punto de captura** que `record_configuration_snapshot` (antes de
  `fit()`).
- Flag nuevo `--capture-environment / --no-capture-environment` en `trainer.py`, **default
  ON cuando `--track-db` está activo** (la grilla siempre lleva `--track-db`, así que las
  corridas gobernadas siempre tendrán lockfile). Off para corridas exploratorias sin
  tracking.
- Qué se captura:
  - **Filas en `environment_packages`**: lista completa `(package_name, package_version)`
    de todas las distribuciones instaladas (≈ `pip freeze`). ~200-400 filas por run.
  - **Subconjunto curado en `run_configuration_snapshots.environment`**: las que importan
    para reproducibilidad numérica —
    `tensorflow`, `keras`, `numpy`, `scipy`, `scikit-learn`, `pillow`, `h5py`,
    `protobuf`, `ml-dtypes` — más `cuda_version` / `cudnn_version` /
    `is_cuda_build` desde `tf.sysconfig.get_build_info()`, y `tf.__version__` /
    `platform`. Esto da lectura rápida sin join a `environment_packages`.
- Sin migración de esquema: `environment_packages` ya existe con la forma correcta
  (`001_schema.sql:235`). Solo se agrega la llamada.

### D2.4 Confirmación: no cambia TRAIN→EVALUATE/EXPLAIN

| Aspecto | Estado |
|---|---|
| `run_lineage` (evaluates_checkpoint_from / explains_checkpoint_from) | **Intacto.** El snapshot no participa del linaje. |
| Query de descubrimiento de EVALUATE/EXPLAIN (`runs ⋈ models ⋈ model_versions`, `run_evaluate_all_trainings.py:72-115`) | **Intacta.** No lee `run_configuration_snapshots`. |
| `model_versions`, `artifacts`, `run_io_records`, `run_clinical_metrics`, ... | **Intactos.** El snapshot es una tabla hija más de `runs`, aditiva. |
| Orden de escritura del ciclo de vida de `runs` (`model_training_pipeline.md` §1.5) | **Sin reordenar.** El `INSERT` del snapshot se intercala entre `start_tracking_run` y el primer `update_execution_tracking`, en su propia transacción; no bloquea ni depende de los demás. |
| `finalize_training_model_version` (verifica SHA-256 del `.keras`) | **Intacto.** |

El snapshot es **información adicional de auditoría/replay**. Un consumidor futuro
(p. ej. un comando `reproduce-run <run_id>`) puede leerlo, pero nada del flujo actual
lo requiere. Si la captura falla (`safe_track` traga la excepción), el training procede
igual — degradación suave, idéntica a como se comporta hoy el resto de tracking.

---

## D3 — Discovery dinámico para el orquestador

### D3.1 `run_train_all_models.py` sin lista hardcodeada

```python
# EJEMPLO — estado propuesto de run_train_all_models.py
from src.malaria_dl.models import iter_model_specs      # auto-discovery de catalog/

def default_models() -> list[str]:
    return [s.name for s in iter_model_specs()]

# config DE GRILLA (no de modelo) — se mantiene, en un solo lugar:
DEFAULT_OPTIMIZERS = ["adam", "adamw", "sgd", "adadelta"]        # P0 (config de grilla)
OPTIMIZER_LEARNING_RATES = {                                     # P3 (config de grilla)
    "sgd": ("1e-3", "1e-4"), "adadelta": ("1.0", "1.0"), "_default": ("1e-4", "1e-5"),
}

def model_run_params(spec) -> dict:                              # reemplaza model_training_params (P2)
    return {
        "fine_tune_epochs": "20" if spec.supports_fine_tuning else "0",
        "pretrained_weights": spec.pretrained_source or "none",
    }
```

- `--models` `choices` y `default` → `default_models()`.
- `build_train_command` toma un `ModelSpec` en vez de un string; lee `fine_tune_epochs`
  y `pretrained_weights` del spec, no de un `if model in {...}`.
- **Agregar un modelo nuevo `efficientnet_b0`**: crear
  `src/malaria_dl/models/catalog/efficientnet_b0.py` con su `ModelSpec` + su builder.
  **Cero ediciones** en `run_train_all_models.py`, `trainer.py`, `tracking.py`,
  `preprocessing.py`. El único otro toque es su test
  (`tests/test_model_catalog.py` parametrizado lo cubre automáticamente si se añade a la
  lista esperada) y — si corresponde — `run_explain_all_trainings.py` sigue descubriendo
  desde BD (sin cambios).

**Import barato:** `iter_model_specs()` importa solo los módulos `catalog/*.py`, que
importan solo `spec.py` (dataclasses + stdlib). **No importan TensorFlow** — el builder
se referencia por string (`builder_ref`) y se resuelve con `importlib` recién dentro de
`src.train`. El orquestador deja de ser "stdlib pura" en sentido estricto (ahora importa
`src.malaria_dl.models`) pero **no carga TF ni abre la BD**; `--dry-run` sigue siendo
instantáneo y offline. Este es el costo mínimo y aceptable (ver §T&O-6).

### D3.2 H3 y H4 — confirmación de que NO se reintroducen ni se resuelven

| Hallazgo | ¿El diseño lo reintroduce? | ¿Lo resuelve de paso? | Estado |
|---|---|---|---|
| **H3** — orquestador no valida `--dataset-version-id` antes de lanzar | **No.** El discovery dinámico no toca la validación de dataset. Sigue igual que hoy (cada `src.train` lo resuelve). | **No.** Fuera de alcance. | **Fuera de este diseño.** Fase posterior: pre-check de 1 query (`list_trainable_dataset_versions`) en `main()` antes del doble bucle. Independiente de D1/D2/D3. |
| **H4** — sin transacción ni reanudación de lote | **No.** El comportamiento de `--continue-on-error` / `break` no cambia. | **Parcialmente habilitado, no resuelto.** D2 introduce `orchestration.batch_id` persistido en `run_configuration_snapshots`. Con eso, una fase futura **puede** consultar "¿qué (modelo,optimizer) del batch X ya tienen run `completed`?" y reanudar. Hoy eso es imposible (mapa §5.1-T1: no hay identidad de lote). | **El mecanismo de reanudación queda fuera**; el `batch_id` que lo hace posible entra como parte de D2. |
| **T7** — intentados vs completados vs excluidos | No | No | Fuera. El `batch_id` + `orchestration.requested_models` permiten reconstruir "intentados" a posteriori, pero no hay registro activo de exclusiones. |

**Resumen:** D3 se limita a matar la lista hardcodeada (H1/H2). H3 y H4 se dejan
**explícitamente para una fase posterior**; D2 deja plantado el `batch_id` como
prerrequisito de H4.

---

## Trade-offs explícitos de cada decisión

### T&O-1 · `ModelSpec` como dataclass en `catalog/<name>.py` (D1.2)

- **Se gana:** una fuente de verdad por modelo; los 13 puntos accidentales colapsan;
  agregar modelo = 1 archivo; los 3 puntos reales quedan como datos que el modelo
  declara sobre sí mismo (nadie conoce a nadie).
- **Se pierde:** una indirección nueva — para saber cómo se construye un modelo hay que
  leer `spec.builder_ref` y saltar a `architectures.py`. Mitigable permitiendo que el
  builder viva en el mismo archivo si el autor quiere.
- **Alternativa descartada — archivo declarativo YAML/TOML + loader:** rompe la
  restricción del responsable (la definición del modelo dejaría de ser Python
  ejecutable; el fine-tuning específico y los callbacks propios no caben en YAML). Además
  duplica: el YAML tendría que re-declarar lo que el builder ya sabe.
- **Alternativa descartada — tabla `model_catalog` en BD poblada por migración:** el
  mapa §2.1 (H1 "no hay migración; el catálogo es dato, no esquema") y
  `model_training_pipeline.md` §2.1 confirman que hoy `models` se puebla en runtime. Meter
  el catálogo en BD haría que agregar un modelo requiera una migración Alembic —
  exactamente el anti-patrón "lista hardcodeada" movido de sitio, y con peor DX.

### T&O-2 · `fine_tune_unfreeze_layers=4` y `ft_epochs=20` declarados en el `ModelSpec`

- **Se gana:** hoy son números mágicos invisibles (`unfreeze_last_layers(n_layers=4)` en
  `architectures.py:339`, `"20"` en `run_train_all_models.py:67`). Declararlos en el spec
  los hace visibles, versionables (`spec_version`) y los captura D2.
- **Se pierde:** el mapa §2 los clasifica como **política uniforme disfrazada de dato
  por-modelo**. Ponerlos en el `ModelSpec` perpetúa esa apariencia — un lector podría
  creer que `n_layers` varía por arquitectura cuando hoy es constante.
- **Mitigación:** el sello v0 (§D1.6) y este trade-off documentan que son política
  uniforme; `ModelSpec` les da un **default compartido** (`fine_tune_unfreeze_layers:
  int = 4` en el dataclass) y solo se sobreescribe si de verdad difiere. Un futuro
  barrido puede moverlos a "config de grilla" sin tocar el contrato.
- **Alternativa descartada — dejarlos solo en config de grilla desde ya:** se pierde la
  capacidad de que un modelo que *sí* necesite un `n_layers` distinto lo declare; y
  `ft_epochs` sí tiene una componente real ("¿este modelo tiene backbone?").

### T&O-3 · Registro por decorador + auto-discovery (D1.3)

- **Se gana:** "crear archivo = modelo registrado", sin editar un índice central.
- **Se pierde:** el registro pasa a depender de un `pkgutil.iter_modules` + imports
  dinámicos → un archivo con error de sintaxis en `catalog/` rompe el discovery entero;
  el orden de registro es no determinista (mitigado ordenando por `name` en
  `iter_model_specs`).
- **Alternativa descartada — convención de filename:** ata el nombre canónico al nombre
  del archivo; renombrar el archivo = renombrar el modelo en BD (revive H5).
- **Alternativa descartada — `MODEL_REGISTRY` explícito editado a mano:** es literalmente
  el estado actual de H2 (existe, hay que acordarse de tocarlo). No cumple D3.1.

### T&O-4 · Tabla `run_configuration_snapshots` vs columna JSONB en `runs` (D2.1)

- **Se gana:** aislamiento transaccional (INSERT propio antes de `fit()`), `runs` liviano,
  y — clave — la guarda de cobertura de esquema de `purge.py` **obliga** a clasificar la
  tabla nueva en el subsistema `--run` (control de gobernanza intencional).
- **Se pierde:** una migración más; hay que actualizar `SUBSYSTEMS` en `scripts/db/purge.py`,
  el conteo 28→29 en `subsystem_data_purge.md` y
  `cell_vs_microscopy_resolution_2026-09-08.md` §8, y los ~29 tests de
  `test_db_purge_tool.py`. Un `JOIN` extra para ver la config de un run.
- **Alternativa descartada — columna `runs.configuration_snapshot`:** más simple de
  escribir pero (a) compite con los `UPDATE runs` del ciclo de vida (merge JSONB), (b)
  engorda una fila ya de ~40 columnas con un blob de decenas de KB, (c) **se escapa** de
  la guarda de purga → datos de config sin punto de control explícito.
- **Alternativa descartada — reusar `runs.execution_parameters`:** ya es un cajón de
  sastre (mapa §4.1); mezclar ahí la topología resuelta lo vuelve ilegible y no resuelve
  el timing (hoy se completa en varias fases, no antes de `fit()`).

### T&O-5 · `resolved_topology` = `model.to_json()` capturado del objeto Keras (D2.1)

- **Se gana:** exactitud total y **cero mantenimiento** — el autor del modelo no escribe
  ninguna descripción; se fotografía el grafo real ya construido. Captura la capa
  `Normalization` de densenet con sus mean/var, cada `Dropout(rate)`, la pila conv de
  custom_cnn.
- **Se pierde:** el JSON de Keras es verboso (densenet121 ≈ 30-60 KB) y su formato es
  interno de Keras (puede cambiar entre versiones de TF → por eso se guarda
  `keras_version` al lado). No es un "diff humano" cómodo.
- **Alternativa descartada — que el `ModelSpec` exponga `describe_topology(resolved_hp)`:**
  obliga a cada modelo a mantener a mano una descripción paralela a su builder → nueva
  fuente de divergencia (el mismo error que este proyecto arrastra). 
- **Alternativa descartada — guardar solo hiperparámetros, no topología:** no cierra el
  hallazgo 0.4 (la topología es justo lo que hoy solo vive en el código de `92e36c72`).

### T&O-6 · El orquestador importa `src.malaria_dl.models` (D3.1)

- **Se gana:** discovery dinámico real; `DEFAULT_MODELS` deja de existir.
- **Se pierde:** `run_train_all_models.py` deja de ser "stdlib pura"
  (`model_training_pipeline.md` §0.1 lo describía así como virtud). Ahora depende del
  paquete del proyecto y de que sea importable (`PYTHONPATH` / editable install).
- **Mitigación:** los módulos `catalog/*` no importan TensorFlow (builder por
  `builder_ref` lazy). El costo real es ~decenas de ms de import de dataclasses, no los
  ~2-3 s de TF. `--dry-run` sigue sin tocar BD ni TF.
- **Alternativa descartada — manifiesto JSON generado (`catalog.lock.json`) que el
  orquestador lee sin importar Python:** agrega un paso de build y un artefacto que se
  desincroniza. El import liviano es más simple y siempre fresco.

### T&O-7 · `environment_packages` siempre ON con `--track-db` (D2.3)

- **Se gana:** las 12+ corridas gobernadas por fin tienen lockfile; reproducibilidad
  numérica auditable.
- **Se pierde:** ~200-400 filas nuevas por run en `environment_packages` (12 runs ≈
  3-5 K filas por grilla — trivial para PostgreSQL). Coste de ~1-2 s de
  `importlib.metadata.distributions()` por run.
- **Alternativa descartada — opt-in con flag:** es el estado actual (`model_training_pipeline.md`
  H: "solo si se habilita explícitamente") y el resultado es 0 filas. Si es opcional, no
  se usa.
- **Alternativa descartada — `pip freeze` por subprocess:** más frágil (depende del `pip`
  del entorno, formato variable). `importlib.metadata` ya está implementado y es estable.

### T&O-8 · Falla ruidosa ante modelo/metadato desconocido (D1.3, D1.4-P14)

- **Se gana:** desaparecen los dos fallos silenciosos del mapa §6.2.5 — el `else`
  catch-all que entrena densenet, y el `model_defaults` faltante que degrada a
  `model_type='unknown'`. Un nombre no registrado ahora levanta `UnknownModelError`.
- **Se pierde:** rigidez — un typo en `--model` que antes "funcionaba raro" ahora aborta
  antes de arrancar TF. (Esto es deseable, pero es un cambio de comportamiento
  observable.)
- **Alternativa descartada — warning + continuar:** es lo que hay hoy y produjo la fila
  huérfana `vgg16` (H5).

### T&O-9 · No retrofitear el snapshot a los 12 runs históricos (D1.6)

- **Se gana:** alcance acotado; sin arqueología de reconstruir topologías de `92e36c72`
  para meterlas en el esquema nuevo.
- **Se pierde:** los 12 runs quedan asimétricos — auditables solo por `git checkout` +
  sello v0, sin fila en `run_configuration_snapshots`. Un dashboard que asuma "todo run
  tiene snapshot" debe manejar el `NULL`.
- **Alternativa descartada — backfill:** el mapa §0.5 y §4 son explícitos en que la
  reproducibilidad histórica ya descansa en `runs.git_commit → 92e36c72` y que **no hace
  falta** retrofitear (prompt §3). Un backfill parcial (sin `environment_packages` reales
  de agosto, que ya no se pueden recuperar) daría falsa sensación de completitud.

---

## Resumen de artefactos a crear/modificar (para dimensionar la implementación)

| # | Archivo | Acción | PR |
|---|---|---|---|
| 1 | `src/malaria_dl/models/spec.py` | nuevo — `ModelSpec` y afines | PR-1 |
| 2 | `src/malaria_dl/models/registry.py` | reescribir — `_CATALOG` + auto-discovery + shim | PR-1 |
| 3 | `src/malaria_dl/models/catalog/{__init__,custom_cnn,vgg16_transfer_learning,densenet121}.py` | nuevos | PR-1 |
| 4 | `src/malaria_dl/models/catalog/_v0_pre_decoupling.md` | nuevo — sello v0 (doc) | PR-1 |
| 5 | `tests/test_model_catalog.py` | nuevo | PR-1 |
| 6 | `src/malaria_dl/training/trainer.py` | `parse_args` choices/validación, dispatch → `build_from_spec`, guards P7/P8 genéricos, `resolve_preprocessing_mode(spec,...)`, P5 | PR-2 |
| 7 | `src/malaria_dl/data/preprocessing.py` | `resolve_preprocessing_mode` toma `spec`; borrar `recommended_preprocessing_mode` substring-match | PR-2 |
| 8 | `src/malaria_dl/persistence/tracking.py` | `model_defaults`/`model_name_*` → wrappers sobre `resolve_spec`; `record_configuration_snapshot` | PR-3 / PR-6 |
| 9 | `alembic/versions/20260909_01_run_configuration_snapshots.py` | nuevo — tabla | PR-6 |
| 10 | `src/malaria_dl/persistence/run_repository.py` | `log_configuration_snapshot`, `collect_runtime_environment_extended` (git_dirty), llamada a `log_environment_packages` | PR-6 |
| 11 | `scripts/db/purge.py` + `docs/operations/subsystem_data_purge.md` + `cell_vs_microscopy_resolution_2026-09-08.md` §8 + `tests/test_db_purge_tool.py` | clasificar la tabla nueva en `--run` (28→29) | PR-6 |
| 12 | `run_train_all_models.py` | discovery dinámico, `--batch-id`/`--orchestrator-context`, `build_train_command(spec)` | PR-4 |
| 13 | `tests/test_governed_dataset_contract.py`, `tests/test_training_selection.py` | ajustar a la nueva firma de `build_train_command` | PR-4 |

Fuera de alcance (fase posterior, mencionados para contexto): pre-check de
`--dataset-version-id` (H3), reanudación de lote por `batch_id` (H4), dedupe de la fila
`models.name='vgg16'` (H5), registro de exclusiones (T7).

---

## Preguntas para el responsable antes de implementar

1. **Ubicación del builder:** ¿`architectures.py` sigue siendo el hogar de las funciones
   `build_*` (spec las referencia por string), o se permite/prefiere que cada
   `catalog/<name>.py` contenga también su builder? (El contrato soporta ambas; afecta
   dónde se hace el fine-tuning específico.)
2. **`ft_epochs` / `n_layers`:** ¿se declaran en el `ModelSpec` (visible pero parece
   dato-por-modelo) o se mueven ya a "config de grilla" (§T&O-2)?
3. **`run_configuration_snapshots`:** ¿tabla nueva (recomendado, §D2.1) o preferencia por
   columna JSONB en `runs` pese a los contras?
4. **`environment_packages` siempre ON con `--track-db`** (§T&O-7): ¿confirmado, o se
   quiere un flag para desactivarlo en corridas gobernadas?
5. **Orquestador con `batch_id`:** ¿ok que `run_train_all_models.py` pase a importar
   `src.malaria_dl.models` (pierde "stdlib pura" pero no carga TF/BD)?
6. **Sello v0 como Markdown** (`_v0_pre_decoupling.md`) vs. como fila real en
   `run_configuration_snapshots` con `run_id = NULL` / marcador especial.
