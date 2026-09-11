# E8 — Ensembles como extensión experimental

**Dictamen técnico: NO APROBADA.** Implementación local y pruebas controladas completadas; integración PostgreSQL E8 y regresión E7 **NO VERIFICADAS** por acceso denegado al socket Docker. **Ejecución científica y superioridad del ensemble: PENDIENTES.** No se inicia E9.

## Línea base

HEAD inicial: `9eb5c721d3d7a39247bd3f0fdb51a9092c11df7a`, rama main, árbol limpio. El cierre E7 ya está versionado. Se leyeron la solicitud E8, contrato 0B v1.1, cierres E6/E7 y contratos de dataset, input, linaje, evaluación, comparación y persistencia. No se encontró `AGENTS.md` aplicable al repositorio ni sus ancestros.

Se verificaron **80/80 hashes** del manifiesto final E7 al comenzar. El cierre E7 registra 79/79 del manifiesto previo y agrega el documento de cierre como entrada 80; no hay contradicción entre esos conteos. Sus **3 pruebas PostgreSQL aprobadas en 2.34s** y rollback con cero eventos desde otra conexión son evidencia aportada por el usuario, no reejecutada aquí. El cierre E6 acredita previamente 17 pruebas y revisión `20260912_02`; no se presenta como nueva lectura de revisión o readiness.

E8 modifica intencionalmente dos entradas de ese manifiesto (`science/cli.py`, `science/repository.py`); las otras **78 permanecen iguales**. También adapta el entrypoint de ensemble y su README. No se alteran informes/manifiestos anteriores ni configuraciones E7 congeladas. La revisión efectiva se identifica por HEAD y el manifiesto E8, sin commit de este trabajo.

## Diagnóstico inicial

| Área | Existente / reutilizable | Faltante / cambio necesario |
|---|---|---|
| Ensemble | `src/ensemble.py` adapta `inference/ensemble.py`; helper de umbral y conversión de probabilidad | Main legacy normalizaba pesos, compartía preprocessing, cargaba modelos y ejecutaba TEST/CSV. Sustituido por flujo E8 sobre fuentes E6 |
| Predicciones | `assessment_results`, identidades e intentos E6; `science.comparison.read_evaluation` | Alinear conjuntos completos por sample_id, validar etiquetas/pacientes/snapshot y conservar contribución por miembro |
| Entrada/clases | Contrato E3 por arquitectura y mapeo `parasitized=1` | Conservar los tres contratos, rechazar inversión y fuentes no acreditadas |
| Linaje | E6 resuelve TRAIN/versión/checkpoint, E5 verifica registros y E1 sella archivos | Reusar lector verificador; rechazar duplicados por checksum y grupos incompatibles |
| Umbral/calibración | E7 regla estricta > 0,98; E6 opera raw sin calibrador aprendido | Umbral E7 sobre combinación VAL, procedencia registrada; calibradores no soportados rechazados |
| Comparación | Métricas, curvas, bootstrap por paciente, SD entre semillas, reportes E7 | Extender matriz y CLI, comparar con cada miembro/baseline, errores y desacuerdo; sin campeón TEST |
| Persistencia | `ScienceRepository` sobre `audit_events` append-only | Tipos separados configuración/evaluación/comparación/fallo, sin TRAIN ficticio ni nuevo esquema |

## Decisiones y alcance implementado

Contrato: `probability_ensemble_e8_v1`; hash `8744f0e7326088b4a7ac419c6439007a655810adb7e38ff6f0dbb2193d5cc001`. Hereda el protocolo científico E7 por versión/hash y añade un documento de extensión, sin modificar el padre.

Promedio uniforme por defecto; ponderado con pesos explícitos predeclarados, finitos/no negativos, suma 1 ± 1e-12 y al menos dos positivos. No se normalizan pesos. Se registra cualquier recorte numérico de probabilidad en el extremo, conservando `combination_sum`; no se confunde con ajustar pesos. No se implementa búsqueda de pesos.

Tres arquitecturas por grupo, mismo TRAIN seed y optimizador, misma población y entorno compatible. Orden canónico por arquitectura, unión por sample_id y prohibición de intersección silenciosa. Se rechaza el mismo checkpoint bajo otra referencia/ruta. Un miembro faltante/fallido aborta la configuración/evaluación entera.

Los scores se consumen raw; calibración del miembro y posterior quedan explícitamente ausentes. No se aplica una calibración dos veces ni se presume que la mezcla esté calibrada. Cada miembro conserva su preprocessing E3 y sus referencias EXPLAIN. No se combinan mapas espaciales.

La configuración guarda modelos, fuentes VAL, pesos, semilla/grupo, snapshot, input contracts, umbral E7 y revisión del código. La evaluación separada registra todas las probabilidades/contribuciones, hashes, métricas, errores corregidos/introducidos y código efectivo (`execution_code`). La comparación reconstruye desde las fuentes antes de aceptar el resultado guardado.

Se heredan IC por paciente y tratamiento de ausencias E7; no se mezclan semillas como nuevas observaciones. La referencia individual se elige en VAL entre los tres miembros del grupo, no como campeón global. La matriz añade 24 grupos ensemble a 72 filas E7; las condiciones sintéticas E7 continúan no disponibles. Pesos ponderados operativos y Run IDs permanecen sin designar.

**Límites deliberados:** esta ruta sólo evalúa combinaciones VAL. TEST está deshabilitado; un flujo final futuro requerirá revisión y autorización de configuración congelada. No se implementan inferencia directa, stacking, selección dinámica, pares, ensembles entre semillas, búsqueda de pesos o calibradores aprendidos. No se presentan como capacidades disponibles. No se midió latencia, ni se atribuye al ensemble el costo de sólo promediar scores.

## Archivos y propósitos

Rutas relativas a `malaria_dl_local_project/`, salvo docs:

| Archivo | Cambio |
|---|---|
| `src/malaria_dl/science/ensemble.py` | Contrato versionado, matriz, pesos/alineación, preparación/evaluación y pruebas de reconstrucción |
| `src/malaria_dl/science/ensemble_repository.py` | Extiende repositorio E7 por tipo de evidencia; lectura verificada, fuentes y configuración persistida obligatorias |
| `src/malaria_dl/science/ensemble_reporting.py` | Reporte ensemble/miembros, exclusiones, matriz observada, grupos de repetición y exportaciones desde BD |
| `src/malaria_dl/science/ensemble_cli.py` | prepare/validate/combine/compare; fallos sanitizados con auditoría separada |
| `src/malaria_dl/science/repository.py` | Parametriza tipo, recurso, fuente, validador y estado de evento; conserva defaults E7 y round-trip |
| `src/malaria_dl/science/cli.py` | Añade `compare-ensembles` |
| `src/malaria_dl/inference/ensemble.py` | Main E8; elimina ejecución legacy de TEST/CSV; conserva helpers históricos |
| `src/ensemble.py` | Propaga código de salida del main gobernado |
| `README.md` | Sustituye comandos y advertencias legacy de ensemble por el flujo E8 |
| `configs/science/e8_v1.json` | Contrato de extensión verificable contra implementación |
| `tests/test_ensemble_e8.py` | 35 casos controlados E8 |
| `tests/test_ensemble_postgres.py` | 3 casos PostgreSQL sintéticos opt-in |
| `docs/science/ensembles_e8_v1.md` | Contrato, decisiones, ejemplo controlado y comandos |
| `docs/science/matriz_e8_v1.json` | 96 filas planificadas, no resultados |
| `docs/science/preparacion_e8_v1.md` | Faltantes operativos/científicos sin cifras simuladas |

Se añaden esta auditoría y el manifiesto E8. No se modificaron tablas, migraciones, publicaciones ni despliegues.

## Pruebas realizadas

Desde `malaria_dl_local_project`:

```sh
.venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/test_ensemble_e8.py tests/test_ensemble_postgres.py \
  tests/test_ensemble_threshold_integration.py \
  tests/test_science_e7.py tests/test_science_postgres.py tests/test_assessment_e6.py
```

**105 passed, 6 skipped, 7 warnings in 15.29s.** Incluye 35 casos E8, compatibilidad de helpers y regresiones E7/E6. Los seis omitidos son 3 PostgreSQL E8 y 3 PostgreSQL E7; no se suman resultados de ejecuciones intermedias. Advertencias de dependencias protobuf/SHAP/Keras en fixtures; no aserciones fallidas.

Ruff sobre archivos Python nuevos/modificados relevantes: **All checks passed**. `git diff --check`: sin errores. Se conserva sin cambios la prueba histórica `test_ensemble_threshold_integration.py`.

| Requisito | Evidencia controlada |
|---|---|
| Promedio uniforme/ponderado | Fixture con scores conocidos: 0.30/0.733333… y 0.36/0.69, respectivamente |
| Pesos | Rechazo de suma incorrecta, negativos, NaN/Inf, booleanos, ausencias y único peso positivo |
| Identidad | Reordenamiento de filas y miembros conserva revisión y resultado; referencias duplicadas rechazadas |
| Población | Rechazo de muestras faltantes/duplicadas, etiqueta/paciente distintos y snapshot/partición incompatibles |
| Probabilidades/input | Rechazo de scores fuera de [0,1], no finitos, mapeo invertido y calibrador desconocido/doble |
| Checkpoint y linaje | Checksum duplicado rechazado; lectura verificada rechaza fuente cambiada; regresiones E6 incluyen versiones ambiguas |
| Sin degradación | Miembro ausente aborta; fallo CLI auditado sin resultado/CSV de fallback |
| Umbral y revisión | Selección E7 determinista; cambio de umbral sin procedencia consistente rechazado; TEST prohibido |
| Errores/desacuerdo | Casos controlados corrigen e introducen errores; desacuerdo identificado por muestra |
| Repeticiones | Tres semillas explícitas, SD/n/N separados, dos predicciones por resultado conservadas; sin pooling |
| Reportes | Exclusiones y matriz observada, JSON/Markdown/PNG desde reporte, configuración máquina igual al contrato |

## PostgreSQL: intento y pendiente

Se revisaron las pruebas y se intentó ejecutar E8 mediante Compose:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE8_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -s -p no:cacheprovider tests/test_ensemble_postgres.py
```

Resultado: **exit 1, pytest no se inició**, `permission denied while trying to connect to the docker API`. No se interpreta como BD caída. No se cambió socket/servicio ni se instaló otra BD.

La regresión E7 también debe reejecutarse porque se parametrizó su repositorio compartido. Comando de cierre pendiente para la terminal del usuario:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE8_POSTGRES_TESTS=1 -e RUN_STAGE7_POSTGRES_TESTS=1 \
  -e PYTHONDONTWRITEBYTECODE=1 backend python -B -m pytest -q -s -p no:cacheprovider \
  tests/test_ensemble_postgres.py tests/test_science_postgres.py
```

| Comprobación | Esperado | Estado obtenido |
|---|---|---|
| Configuración/evaluación/comparación | Tres eventos, lectura idéntica, referencias y tipos separados, idempotencia | NV por socket |
| Append-only | UPDATE rechazado; outer transaction utilizable | NV |
| Escritura fallida | Cero evaluación parcial, savepoint utilizable, fallo con success=false/error_code | NV |
| Configuración obligatoria | Rechazo de configuración ausente o tipo de evento incorrecto | NV |
| Rollback | Cero eventos ensemble desde otra conexión; limpieza del esquema sintético | NV |
| Regresión repositorio E7 | Tres casos previos siguen pasando con la parametrización | NV en la revisión E8 |

Se reutiliza el fixture E4: esquema aleatorio validado, copia de estructura audit y triggers append-only. Para comprobar visibilidad desde otra conexión se confirma únicamente la preparación del esquema sintético y luego se inicia una transacción externa para las escrituras E8. Los commits internos quedan en savepoints. Finalmente rollback y consulta READ ONLY desde otra conexión; limpieza/ausencia del esquema según fixture vigente. No hay DELETE de eventos ni desactivación de constraints.

Las fuentes del caso E8 de persistencia son fixtures en memoria; no acredita dataset ni candidatos reales. La lectura y alineación se prueban separadamente con fuentes controladas y regresiones E6. No se equipara rollback a durabilidad de un commit entre sesiones ni resistencia a caída física. Las lecturas operativas del flujo usan la vía READ ONLY de E7/E1; las escrituras de evidencias son transacciones separadas. No se requiere migración E8.

## Cierre y pendientes separados

**Técnico:** E8 permanece NO APROBADA hasta verificar los seis casos PostgreSQL (tres E8 y tres de regresión E7) en la instancia Compose autorizada. No hay otro bloqueo local conocido.

**Científico:** faltan ejecuciones E7 autorizadas, fuentes E6 de tres miembros por grupo, designación previa de pesos ponderados, acreditación actual de dataset/población y evaluación comparativa VAL. El sesgo por selección compartida sigue explícito. La superioridad, calibración clínica, cumplimiento del objetivo y latencia completa no se acreditan por fixtures.

No se ejecutaron entrenamientos completos, búsqueda operativa de pesos, inferencia TEST, combinación operativa, promociones, reset o limpieza de almacenamiento del proyecto. Se preservaron datasets, split, imágenes/checkpoints existentes y publicaciones. Producción permanece manual. E9 no se inicia.

Entregables humanos: [contrato y comandos](../science/ensembles_e8_v1.md), [matriz](../science/matriz_e8_v1.json), [reporte de faltantes](../science/preparacion_e8_v1.md).
