# Malaria Dataset Split Project

## Propósito y estado actual

Construir y gobernar datasets experimentales reproducibles para el proyecto de malaria.
El pipeline oficial está implementado de extremo a extremo: descubrimiento, identidad
clínica, bootstrap científico, split agrupado por paciente, persistencia, validación,
materialización, reconciliación, freeze y derivación de trainability.

La versión vigente es:

```text
Malaria Patient Split v1
dataset_version_id = d8c0cab5-09dd-597f-9de7-7ca01aee2ec2
status = FROZEN
trainable = YES

201 pacientes / 27.558 imágenes
TRAIN 22.180 / VAL 2.693 / TEST 2.685

12/12 checks = PASS
materialization = READY
reconciliation = PASS
```

PostgreSQL es el source of truth científico; el filesystem versionado es una
materialización derivada. Una versión `FROZEN` es inmutable. El split físico histórico
se audita y conserva, pero no es fallback para nuevos TRAIN gobernados.

## Fuera de alcance

Este paquete no entrena ni evalúa modelos y no implementa inferencia, producción,
Grad-CAM o detección. `malaria_dl_local_project` consume la Dataset Version entrenable;
este proyecto conserva la capacidad oficial de construir futuras versiones, incluida
una eventual `Malaria Patient Split v2`.

`malaria_dataset_split_project` prepara, versiona, valida y materializa datasets;
`malaria_dl_local_project` entrena y evalúa modelos.

## CLI

Desde este directorio, con el entorno del proyecto ML:

```bash
SPLIT_PYTHON=../malaria_dl_local_project/.venv/bin/python
PYTHONPATH=src "$SPLIT_PYTHON" -m malaria_split.cli --help
```

Los entrypoints vigentes son:

```text
audit-current-split
audit-patient-identity
audit-system-contracts
bootstrap-malaria-v1
audit-scientific-bootstrap
audit-patient-profiles-v1
generate-patient-split-v1
persist-patient-split-v1
validate-patient-split-v1
materialize-patient-split-v1
freeze-patient-split-v1
```

Los tres primeros son auditorías; los comandos de persistencia/materialización/freeze
aplican sus propios guards, transacciones e idempotencia. Use el runbook antes de una
operación que escriba en PostgreSQL o filesystem:
`../docs/runbook_split_completo_malaria.md`.

La instalación del paquete también expone `malaria-split` mediante
`malaria_split.cli:main`.

## Pruebas

La suite unitaria no modifica datasets ni artefactos:

```bash
PYTHONPATH=src "$SPLIT_PYTHON" -m pytest -q tests/unit
```

Las pruebas de integración requieren un `DATABASE_URL` explícito hacia una base
PostgreSQL de test con el schema vigente; sus fixtures escriben sólo dentro de
transacciones con rollback. No deben apuntarse a producción.

La evidencia y decisiones por etapa permanecen en `docs/`; esos documentos son
auditorías históricas y no deben interpretarse como el estado operativo actual.
