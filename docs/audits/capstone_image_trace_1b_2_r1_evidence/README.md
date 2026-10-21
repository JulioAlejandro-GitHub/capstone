# TRACE.1B.2-R1: reproducción experimental

Todos los comandos desde raíz del repositorio, Python `malaria_dl_local_project/.venv-metal/bin/python`, macOS Apple M4 Max con GPU Metal visible. No instalar dependencias, no descargar pesos. Los destinos deben ser nuevos; no ejecutar una suite encima de esta evidencia. Cambiar HERE/ROOT a un directorio experimental nuevo o copiar sólo arneses a otra carpeta de auditoría con la misma profundidad.

1. `suite.py`: A/A y A/B; puerta A/A por arquitectura. Reutiliza compare.py anterior sin editarlo.
2. `extended.py`: diagnóstico separado, cinco pares alternados por arquitectura, controles augmentation/shuffle, bytes duplicados, 30 épocas y excepciones antes/durante/después. Cada proceso termina antes del siguiente.
El intento inicial sin shuffle falló antes de entrenar por firma del wrapper. `resume_controls.py` conserva ese intento y completa el resto. La firma quedó corregida en `experiment.py`; `experiment_benchmarked.py` conserva exactamente la versión usada en los 15 pares (rama sin shuffle no ejecutada).

3. `test_ledger.py`: pruebas de integridad, idempotencia, conflicto, reapertura, límites y fallos.
4. `storage_stress.py`: 200 ámbitos de recibos y muerte abrupta del proceso de almacenamiento; no son pasos GPU.
5. `finish_suite.py`: comparaciones diagnósticas exactas (incluidos tokens), estrés con GC, capacidad, preparación sin modelo, fallo de escritura durante TRAIN, SIGKILL de un TRAIN sintético, sondas de drenaje y verificadores finales.

`experiment.py /directorio/nuevo --deterministic [--observer] [--architecture custom_cnn|vgg16|densenet121] [--two-phases]` reproduce un brazo. `--reference` es sólo diagnóstico; en A transporta tokens sin emitir recibos, en B captura la misma salida del paso original. `--duration-epochs 30` deshabilita EarlyStopping exclusivamente en el control de duración.

La primera suite precede a pequeñas mejoras del validador/journal y de la telemetría; los pares de rendimiento utilizan el agregador final sin cambios durante la campaña. El esquema matemático/tokenizado se conserva. `storage_stress_interrupted.py` preserva el primer intento de estrés detenido por costo diagnóstico; su carpeta parcial no cuenta como éxito.

`token_manifest.json` resuelve tokens; `journal/<scope_hash>/<sequence>.json` conserva eventos canónicos. No mezclar almacenes de distintos brazos: cada fixture aislado reutiliza UUID sintético para comparabilidad, no son RUN operativos. `recover_pending.py` sólo recupera archivos completos y verificables; mantiene truncados como desconocidos. Los timestamps de ejecución están en logs/entorno; las claves de recibo no dependen de timestamps.

No ejecutar estos parches con datos reales. Son hooks privados de la versión Keras medida, aislados en procesos; no integración de producto ni autorización de TRACE.1B.3.
