# Evidencia TRACE.1B.2-R2

Laboratorio sintético local Metal. El dictamen está en
`../capstone_image_trace_1b_2_r2_metal.md`; resultados principales en
`reproduction_performance.json` y `final_performance.json`.

Todos los destinos retenidos son históricos e inmutables. **No volver a ejecutar
estos runners sobre esta carpeta.** Para reproducir, preparar otra carpeta de
laboratorio con la misma profundidad y destinos nuevos, conservar referencias
de lectura a R1 y registrar nuevos sellos antes de medir. Los arneses rechazan
destinos de entrenamiento existentes. Los analizadores heredados pueden escribir
resúmenes: no ejecutarlos sobre resultados históricos que se desee preservar.

## Entorno y comandos ejecutados

Desde la raíz del repositorio, intérprete:
`malaria_dl_local_project/.venv-metal/bin/python`.
Variables: `PYTHONDONTWRITEBYTECODE=1`,
`MPLCONFIGDIR=/private/tmp/trace-r2-mpl`.
Los procesos TRAIN requieren acceso local real a Metal; dentro del sandbox la
GPU no es visible. No se usa CPU como alternativa para entrenar.

Secuencia principal, siempre sin entrenamientos concurrentes:

1. `campaign.py reproduction`: 30 procesos R1 originales, 15 comparaciones A/B.
2. `freeze_runtime.py before_diagnostics`; `integrity.py before_diagnostics`.
3. `profile_campaign.py`: 15 perfiles separados, comparación científica.
4. `analyze.py profiles`; `parse_xplane.py`: análisis de host/XPlane.
5. `phase_campaign.py` y `phase_campaign_v2.py`: cada uno se detuvo en su primer
   diagnóstico por error Metal; ambos intentos y fuentes quedan preservados.
6. Decisión documentada, única optimización del observador y `candidate_v1.json`.
7. `post_profile_campaign.py`: snapshot runtime; `regression_campaign.py`;
   `candidate_profile_campaign.py`; `campaign.py final`; `analyze.py final`.
8. Análisis finales, `historical_science.py`, `recovery_profile.py` (12 simulaciones
   sólo de journal), verificador de recibos, integridad
   histórica, `closeout.py`, figura, informe e inventario.

Los archivos `*_seal.json` contienen timestamp, fuentes SHA256 y argumentos
exactos antes de cada campaña. Las fuentes operativas/instaladas se registraron
en `*_runtime_sources.json`. El sello inicial de reproducción cubre los arneses
originales; el snapshot ampliado de runtime es posterior a esa reproducción,
no se presenta como capturado antes de ella.

## Qué contiene cada familia

- `reproduction_*`: R1 exacto archivado, fixture/config originales.
- `final_*`: cinco pares nuevos por arquitectura con candidato R2.
- `diagnostic_*`: profiling intrusivo; nunca tiempos de aceptación. Las variantes
  tokens/memory/serialization no acreditan durabilidad. `diagnostic_candidate_*`
  verifica la desaparición del bucle redundante de numpy y la ciencia.
- `phase_profile*`: intentos inválidos de separar kernels mediante marcadores;
  revisar `profiling_limitations.md` antes de interpretar esos archivos.
- `*_aa*`, `*_b`, `*_reference_*`, `*_state_*`: puertas científicas y capturas
  del mismo forward/gradientes, pesos/optimizador iniciales y restaurados.
- Controles no-augment, no-shuffle, duplicate, unresolved, fault_*, write_failure,
  killed_training, preparation_control, duration_30_epochs, capacidad/estrés y
  sondas de drenaje/asignaciones: matriz R1 reejecutada sobre el candidato.
- `timings.json`, `outcome.json`, `environment.json`, `configuration.json`,
  manifests, records, journals, NPZ y checkpoints: resultados brutos por proceso.
- `performance.json` vacío procede de summarize.py heredado, invocado antes de
  la serie final y cuyos prefijos no corresponden a R2. **No es el resultado de
  aceptación.** Usar exclusivamente los dos JSON principales indicados arriba.

El cambio candidato está sólo en observer.py: mantiene token.numpy() y las
dependencias de finalización y elimina el bucle adicional de metric.numpy().
`optimization_outcome.md` documenta que gran parte del costo se desplazó a la
lectura del arnés: reducir llamadas no demostró ahorro neto ni estabilización.
ledger.py es idéntico a R1. experiment.py contiene la corrección opcional
no-shuffle que R1 ya conservaba; experiment_benchmarked.py es su archivo exacto
anterior. Esa rama opcional no se ejecuta en los benchmarks.

No hay SQL, E10, datos clínicos, integración operativa, instalación, descarga de
pesos, commit ni push. Ningún resultado habilita automáticamente TRACE.1B.3.
