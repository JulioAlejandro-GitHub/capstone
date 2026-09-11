# E8 — Ensembles experimentales de probabilidades

Versión: `probability_ensemble_e8_v1`.
Hash canónico del contrato de extensión: `8744f0e7326088b4a7ac419c6439007a655810adb7e38ff6f0dbb2193d5cc001`.
Protocolo científico padre: `capstone_science_e7_v1`, hash `7db076d71c2143934f0b3bae47ff253f18d3f65c5c3f8efb2634586acbadbdf2`.

El contrato legible por máquina está en `malaria_dl_local_project/configs/science/e8_v1.json`; una prueba exige igualdad con `science.ensemble.extension_contract()`. Cada configuración concreta tiene además su UUID lógico de ensemble, revisión SHA-256 del contenido y evento PostgreSQL propio. No se altera el protocolo E7 congelado.

## Alcance y reutilización

La ruta anterior `src.ensemble` cargaba modelos por ruta, normalizaba pesos sin validar, compartía preprocessing y ejecutaba TEST con exportación CSV. Su entrada principal ahora conduce al flujo E8 de predicciones E6 verificadas. Se conservan los helpers históricos de consulta de umbral para compatibilidad; no conservan una ruta de ejecución TEST. Los argumentos operativos antiguos `--models` ya no ejecutan inferencia.

E8 usa `science.comparison.read_evaluation` para acreditar cada fuente: TRAIN → versión → checkpoint/hash → contrato E3 → snapshot E1 → intento EVALUATE E6 → predicciones completas. Conserva las referencias de EXPLAIN verificadas de cada miembro. No carga modelos, no llama fit/predict y no adapta las tres arquitecturas a un preprocessing común.

## Estrategias y orden de operaciones

La estrategia por defecto es **uniforme**, exactamente tres arquitecturas: Custom CNN, DenseNet121, VGG16, en ese orden canónico. El promedio es la suma de sus probabilidades dividida por 3. Los pares y ensembles entre semillas no están habilitados.

El promedio **ponderado** exige un peso por referencia explícita, números finitos no negativos, suma 1 con tolerancia absoluta `1e-12` y al menos dos pesos positivos. No normaliza pesos incorrectos. Exige procedencia `predeclared` y una referencia no vacía a la especificación previa. No hay selector ni búsqueda de pesos, operativa o implícita.

Orden: probabilidad raw del miembro → calibrador del miembro (ninguno soportado en esta revisión) → suma ponderada → calibrador posterior (ninguno soportado) → umbral E7. Calibradores desconocidos, scores ya calibrados y dobles aplicaciones se rechazan. El promedio no se declara calibrado.

Se conserva `combination_sum` antes del ajuste numérico. Únicamente un resultado fuera de [0,1] por redondeo dentro de la tolerancia se recorta al extremo; el valor original y todos los pesos/contribuciones quedan registrados. No se redistribuyen pesos.

Cada muestra se une por `sample_id`, nunca por posición ni intersección. Se exigen poblaciones completas e idénticas, paciente y etiqueta coherentes, mismo snapshot/partición, mapeo `uninfected=0`, `parasitized=1`, probabilidad finita, checkpoint e input contract acreditados. Checkpoints con igual SHA-256 se rechazan aunque tengan rutas/UUID distintos. Un miembro faltante o fallido detiene la operación completa y registra fallo; no se degrada a dos miembros.

## Grupos de repetición y protocolo

Cada grupo contiene una ejecución de cada arquitectura con **la misma semilla TRAIN y optimizador**, configuración congelada E7 y entorno compatible. Las semillas permitidas siguen siendo 11, 29 y 47; los Run IDs y referencias E6 son explícitos. No se combinan automáticamente semillas.

La matriz E8 conserva las 72 filas E7 (36 originales y 36 sintéticas no disponibles) y añade 24: uniforme y ponderado × cuatro optimizadores × tres semillas. [Matriz explícita](matriz_e8_v1.json). Los miembros, dataset y pesos ponderados siguen pendientes hasta que existan referencias acreditadas. El comparador marca únicamente las referencias seleccionadas como evaluadas; no inventaría el estado de experimentos no consultados.

La elección de miembros y umbral sigue siendo adaptativa aunque el promedio uniforme no ajuste pesos. Se reutiliza la regla E7 sobre VAL: sensibilidad **> 0,98**, luego especificidad, F2 y mayor umbral. No se relabelan predicciones históricas. El umbral seleccionado y el hash de scores VAL quedan en la revisión de configuración antes de generar su evento de evaluación. Un cambio de miembros, pesos, fuente o umbral cambia la revisión; no hay UPDATE de la configuración.

VAL compartida implica optimismo por selección. El estado es siempre exploratorio. Los IC mantienen modelos/umbral fijos y remuestrean pacientes completos; no corrigen todo ese optimismo. Se heredan de E7 mínimo de grupos, réplicas, tratamiento de métricas indefinidas y definiciones de ROC-AUC/AP. AP es average precision no interpolada. La SD muestral entre semillas es separada de la incertidumbre por pacientes.

TEST está deshabilitado en esta revisión de ejecución E8, incluso si ya existen predicciones TEST de miembros. Una futura capacidad final requerirá autorización explícita y validación de la configuración congelada, sin cambiar pesos/umbral. Esta entrega no acredita que ese flujo futuro esté implementado. No se crean TRAIN ficticios ni se reutiliza indebidamente un bloqueo E6 de un modelo individual para autorizar un ensemble.

## Persistencia, comparación y artefactos

Se extiende el repositorio E7, sin tablas nuevas:

| Tipo de evento en `audit_events` | Contenido |
|---|---|
| `ml.ensemble_configuration` | Definición, revisión, modelos/checkpoints/inputs, pesos, calibración explícita, fuentes VAL, umbral y código |
| `ml.ensemble_evaluation` | Referencia de configuración, todas las probabilidades y contribuciones por muestra, hashes, métricas, curvas, IC y contraste con miembros |
| `ml.ensemble_comparison` | Selección explícita de eventos de evaluación, exclusiones, matriz, resultados y variabilidad por grupos |
| `ml.ensemble_failure` | Fallo sanitizado con `success=false` y `error_code`; no resultado parcial verified |

Los UUID de eventos son deterministas sobre el contenido, igual que E7. Inserción atómica, idempotencia, lectura posterior e igualdad obligatorias; no hay ledger de archivos. Configuración y evaluación son eventos separados, sin registrar un nuevo TRAIN. La evaluación registra también `execution_code` con hashes del código y versiones reales, separado del código con que se preparó la configuración. La evaluación conserva el detalle completo por muestra en JSONB; sus fuentes siguen en `assessment_results` de E6.

Antes de comparar, `EvaluationRepository.read_verified` reconstruye desde las fuentes E6 y exige igualdad con el resultado guardado. Un cambio de checkpoint, fuente, evidencia o código efectivo que impida reconstruir exactamente el resultado se excluye con motivo. Los grupos con distinta población, configuración, pesos o código no se agregan juntos; repeticiones ambiguas se excluyen. La referencia individual se elige **en VAL dentro del grupo explícito de tres miembros**, con sensibilidad > 0,98, especificidad, F2 y arquitectura estable. No es un campeón global ni una elección retrospectiva de TEST.

El reporte incluye ensemble frente a cada miembro, baseline siempre parasitized, errores corregidos/introducidos por sample_id, rango de scores y desacuerdo de decisiones. El desacuerdo es descriptivo, no incertidumbre clínica calibrada. Las contribuciones numéricas no son explicación espacial conjunta: no se promedian mapas Grad-CAM. Los enlaces/referencias EXPLAIN pertenecen a sus miembros.

JSON, Markdown y curvas PNG/SVG sólo se exportan después de persistir y releer el reporte; una carpeta con otro reporte se rechaza. Sin fuentes válidas se genera preparación/faltantes, no un ganador. No se mide latencia; tiempos de combinación e inferencia completa permanecen separados y ausentes.

## Ejemplo exclusivamente controlado

Esta tabla reproduce `test_uniform_weighted_known_values_and_reports`. Son scores de fixture, **no imágenes ni resultados clínicos del proyecto**. Pesos declarados del fixture: Custom 0,2; VGG16 0,3; DenseNet121 0,5.

| Etiqueta ficticia | Custom | VGG16 | DenseNet121 | Uniforme | Ponderado |
|---|---:|---:|---:|---:|---:|
| uninfected | 0,1 | 0,3 | 0,5 | 0,30 | 0,36 |
| parasitized | 0,9 | 0,7 | 0,6 | 0,733333… | 0,69 |

El orden del archivo o de los miembros no cambia el resultado. La población mínima del fixture no permite IC por paciente; se devuelve ausencia con motivo. Otros fixtures verifican errores introducidos/corregidos y grupos de tres semillas sin concatenar predicciones.

## Comandos reproducibles

Validación local controlada (sin BD ni datos operativos), desde `malaria_dl_local_project`:

```sh
.venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_ensemble_e8.py
```

Integración y regresión PostgreSQL pendientes en Compose, porque cambió la parametrización compartida del repositorio E7:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE8_POSTGRES_TESTS=1 -e RUN_STAGE7_POSTGRES_TESTS=1 \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m pytest -q -s -p no:cacheprovider \
  tests/test_ensemble_postgres.py tests/test_science_postgres.py
```

Son tres casos E8 y tres de regresión E7. Sólo esquema sintético, rollback/savepoints y limpieza vigente. El caso E8 de documentos usa fuentes controladas en memoria: acredita persistencia, no un dataset operativo. No se ejecuta `make db-migrate`.

Para una futura combinación VAL autorizada, preparar un archivo de solicitud **de configuración** (no de predicciones):

```json
{
  "ensemble_id": "UUID_ENSEMBLE",
  "members": [
    {"evaluation_id": "UUID_EVALUATE_CUSTOM"},
    {"evaluation_id": "UUID_EVALUATE_VGG16"},
    {"evaluation_id": "UUID_EVALUATE_DENSENET121"}
  ]
}
```

Los textos `UUID_*` son marcadores que deben sustituirse por UUID reales explícitos. Al omitir estrategia/procedencia se usa uniforme sin ajuste. Para ponderado se requieren `"strategy":"weighted"`, un campo `weight` por miembro y `"weight_provenance":{"kind":"predeclared","reference":"REFERENCIA_DE_LA_ESPECIFICACION"}`. No hay ingesta de archivos laterales de resultados.

```sh
# Lee fuentes E6 VAL, fija umbral E7 y persiste configuración; no hace inferencia.
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m src.ensemble prepare \
  --request /app/solicitud_ensemble.json

# Valida estructura/hash de una configuración registrada; no acredita de nuevo archivos fuente.
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m src.ensemble validate \
  --configuration-id UUID_CONFIGURATION_EVENT

# Revalida fuentes exactas y combina probabilidades VAL; persiste evaluación separada.
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m src.ensemble combine \
  --configuration-id UUID_CONFIGURATION_EVENT

# Extensión integrada en el comparador E7; no llama inferencia.
docker compose exec -T -w /app/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m src.malaria_dl.science.cli compare-ensembles \
  --evaluation-id UUID_ENSEMBLE_EVALUATION --export-dir /app/artifacts/science/e8-comparison
```

`validate --configuration RUTA.json` valida un snapshot de configuración sin BD y declara explícitamente `structure_and_hash_only`. `src.ensemble compare` ofrece el mismo comparador; sin IDs registra un reporte de preparación en PostgreSQL, no una comparación científica. Ninguno de estos comandos operativos de preparación/combinación fue ejecutado en esta entrega.

## Pendientes y restricciones

Falta verificar PostgreSQL en la revisión E8 y ejecutar posteriormente el protocolo científico autorizado. No se acredita superioridad, sensibilidad del proyecto, calibración clínica ni latencia. Las extensiones futuras (pares, pesos aprendidos, calibradores aprendidos, inferencia directa o TEST con autorización congelada) no se presentan como disponibles. No se implementan stacking ni selección dinámica. Producción permanece manual y E9 no se inicia.
