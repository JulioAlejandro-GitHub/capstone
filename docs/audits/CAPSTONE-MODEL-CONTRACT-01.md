# CAPSTONE-MODEL-CONTRACT-01

Fecha: 2026-10-27. Estado: retiro implementado; registro genérico de TRAIN lógico pendiente de decisión sobre alcance del esquema.

Se retiraron el contrato Python congelado y las dos instalaciones SQL específicas solicitadas. Se retiraron también sus consumidores exclusivos (repositorio, servicio y CLI de registro), en lugar de trasladar sus validaciones a otros módulos. El verificador común de artefactos ya no reconoce el esquema particular de ese protocolo.

`public.models` continúa como catálogo mediante `persistence.run_repository.get_or_create_model`. Los puntos comunes para persistir ejecuciones y artefactos son `start_run`, `log_artifact` y `finish_run`; para versiones con propiedad del checkpoint validada existe `governance.repository.create_model_version`. No se agregó SQL ni un nuevo registro específico del modelo.

El descriptor no entrenable conserva la omisión del TRAIN computacional, incluida la continuación de fuentes entrenables en planes mixtos. Esa omisión no crea un TRAIN lógico ni prueba que se haya registrado un origen. No se fabricaron épocas, métricas, sesiones verificadas ni configuraciones de optimización.

## Limitación encontrada

El esquema versionado exige una fila en `run_configurations` para todo RUN `training`, mediante `v2_run_configuration_required`. Esa tabla exige parámetros de optimización. Por tanto, los repositorios comunes no bastan actualmente para registrar un TRAIN lógico sin aprendizaje. El flujo retirado resolvía esto mediante funciones especiales. No se reprodujo esa excepción ni se alteró el esquema. El resultado integral solicitado aún requiere resolver esta capacidad común; no se declara operativo un reemplazo de registro de extremo a extremo.

## Verificación

Desde `malaria_dl_local_project`, con `PYTHONPATH=.` y Python del entorno `/Users/julio/.cache/capstone-biomedclip-01b/venv/bin/python`:

- `-m pytest tests/test_biomedclip_pretrained.py tests/test_execution_contracts.py -q`: 89 passed.
- `-m pytest tests/test_artifact_tracking.py tests/test_train_run_persistence.py tests/test_execution_contract_dependencies.py -q`: 9 passed, 1 failed (README_2.md ausente), 5 errores de preparación de requisitos sintéticos PostgreSQL.
- `-m pytest tests/test_model_governance_repository.py -q`: 6 passed.
- El primer intento desde la raíz, sin `PYTHONPATH`, falló al importar `src`; se corrigió el directorio de ejecución.
- `git diff --check`: sin errores.

La búsqueda de dependencias ejecutables no encuentra imports ni llamadas a los contratos retirados. El informe anterior está marcado histórico. Su manifiesto y los resultados científicos conservan referencias históricas deliberadamente: alterarlos invalidaría la evidencia original. No se modificaron registros PostgreSQL, checkpoints, pesos ni archivos de evidencia.
