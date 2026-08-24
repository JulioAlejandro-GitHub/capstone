# Runbook operativo: Patient Split de malaria

> **Estado documental: CURRENT_DOC / RUNBOOK CANÓNICO.** Operación local sobre
> PostgreSQL 17 Homebrew y la base persistente `malaria_experiments`. Docker puede
> existir como capacidad opcional del repositorio, pero no es el runtime canónico de
> este procedimiento. Este runbook no inicia, detiene ni reemplaza servicios.

## Estado protegido

La versión oficial ya está materializada y congelada:

```text
dataset_version_id=d8c0cab5-09dd-597f-9de7-7ca01aee2ec2
name=Malaria Patient Split v1
status=FROZEN
trainable=true
patients=201
images=27558
train=22180
val=2693
test=2685
validation=12/12 PASS
materialization=READY
reconciliation=PASS
```

`FROZEN` significa inmutable. Para esta versión están prohibidos el bootstrap,
la persistencia de un nuevo reparto, la rematerialización, el movimiento de su raíz,
la eliminación de archivos y cualquier corrección manual de estados. Un cambio
científico exige una nueva Dataset Version con otro identificador.

## 1. Precondiciones canónicas

Desde la raíz de `capstone`:

1. PostgreSQL 17 Homebrew debe estar disponible en el host.
2. La base operativa debe ser `malaria_experiments`.
3. `DATABASE_URL` debe llegar desde el entorno privado del operador. Esta guía no
   contiene usuarios, contraseñas ni DSN personales.
4. `JWT_SECRET` también debe estar definido porque los guardrails DB reutilizan la
   configuración validada del backend; no se imprime ni se persiste.
5. Backend, ML y CLI de split deben resolver la misma `DATABASE_URL`.

Comprobar que la variable exista sin imprimir su valor:

```bash
: "${DATABASE_URL:?Define DATABASE_URL en tu entorno privado}"
: "${JWT_SECRET:?Define JWT_SECRET en tu entorno privado}"
make db-status
make db-migrate-check
```

Si el servicio, la base o el head Alembic no coinciden con la configuración vigente,
detener el procedimiento. No liberar puertos, cambiar de instancia, iniciar Docker ni
alterar servicios desde este runbook.

## 2. Preparar el CLI

```bash
cd malaria_dataset_split_project
export PYTHONPATH=src
SPLIT_PYTHON=../malaria_dl_local_project/.venv/bin/python

"$SPLIT_PYTHON" -m malaria_split.cli --help
```

El CLI hereda `DATABASE_URL`; no debe sustituirla por un valor por defecto ni por una
base alternativa.

## 3. Auditorías de baseline y gobernanza

Las siguientes operaciones no cambian PostgreSQL ni la composición o
materialización de ninguna Dataset Version. No todas son read-only respecto del
filesystem: `audit-patient-identity` y `audit-system-contracts` regeneran artefactos
derivados bajo `malaria_dataset_split_project/var/audit/`. No ejecutarlas si esos
reportes deben conservarse byte a byte; copiar la evidencia existente antes de
actualizarlos.

```bash
"$SPLIT_PYTHON" -m malaria_split.cli audit-current-split
"$SPLIT_PYTHON" -m malaria_split.cli audit-patient-identity
"$SPLIT_PYTHON" -m malaria_split.cli audit-system-contracts
"$SPLIT_PYTHON" -m malaria_split.cli audit-scientific-bootstrap
"$SPLIT_PYTHON" -m malaria_split.cli audit-patient-profiles-v1 \
  --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2
```

`audit-current-split` y `audit-patient-identity` leen por defecto
`malaria_dl_local_project/data/malaria_physical_split`: ese directorio es el baseline
físico legacy, no la materialización gobernada de v1. Sus resultados sirven para
comparación histórica y no acreditan por sí solos el estado `FROZEN`, los checks ni la
reconciliación de la versión oficial.

Antes de entrenar, completar también la verificación gobernada de la sección 4 y
confirmar en conjunto:

- 27.558 imágenes y 201 pacientes;
- 100 % de cobertura Patient-ID y cero conflictos de identidad;
- cero intersección de pacientes entre `train`, `val` y `test`;
- 12/12 validaciones `PASS`;
- materialización `READY` y reconciliación `PASS`;
- versión `FROZEN` y `trainable=true`.

El leakage del split físico legacy es evidencia histórica esperada; nunca habilita
fallback para un TRAIN gobernado nuevo.

## 4. Verificación en la aplicación

Abrir la URL configurada para el frontend. Con Vite local, el valor por defecto es:

```text
http://localhost:5173/modelo-ia/dataset?datasource=malaria
```

La UI debe mostrar la versión oficial, sus counts, integridad patient-disjoint,
12/12 checks, materialización `READY/PASS` y las ejecuciones realmente vinculadas
mediante `runs.dataset_version_id`. Los runs legacy con valor nulo no pertenecen a v1.

## 5. Entrenamiento y linaje

Para máxima reproducibilidad se recomienda entregar explícitamente:

```text
--dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2
```

Con el flag, el TRAIN resuelve exactamente ese UUID. Si se omite, el resolver ML v1
selecciona sólo entre Dataset Versions `FROZEN` con materialización `READY/PASS` y los
12 checks requeridos más recientes en `PASS`; elige la más reciente y falla si no
existe ninguna. Esa lista de 12 checks es explícita: el resolver actual no promete
incorporar automáticamente checks bloqueantes futuros ajenos a ella. En ambos casos
persiste el UUID resuelto y EVALUATE hereda exactamente la misma versión. Nunca existe
fallback silencioso a `malaria_physical_split`.

## 6. Incidentes de materialización

Ante una raíz ausente, adicional, incompleta o no reconciliada:

1. detener TRAIN y cualquier operación de escritura del pipeline;
2. conservar sin cambios PostgreSQL, la raíz versionada y toda evidencia disponible;
3. ejecutar sólo consultas que no muten PostgreSQL ni las raíces de datos; no
   regenerar artefactos derivados si forman parte de la evidencia preservada;
4. comparar el estado con backups y manifests verificados;
5. preparar un plan de recuperación separado, revisado y autorizado.

No mover, renombrar, borrar ni volver a crear la raíz de v1 para hacerla coincidir con
una base distinta. Tampoco forzar estados SQL. Una materialización exitosa en otro
entorno no autoriza reemplazar la evidencia oficial.

## 7. Futuras Dataset Versions

El ciclo científico reutilizable sigue siendo:

```text
DRAFT → GENERATED → VALIDATED → READY/PASS → FROZEN/TRAINABLE
```

Para crear v2 o una versión posterior se requiere antes:

- nuevo UUID, semver, configuración y freeze contract;
- comandos/configuración que acepten explícitamente esa nueva identidad;
- dry-run y rehearsal transaccional;
- materialización en una raíz nueva, nunca sobre v1;
- 12/12 checks, reconciliación y revisión científica antes de congelar.

Los comandos cuyo nombre termina en `-v1` no deben reutilizarse para una versión
futura sin una implementación y validación específicas.

## Cuándo detenerse

Detener el procedimiento si:

- algún componente resuelve otra base;
- `DATABASE_URL` falta o no corresponde al entorno operativo aprobado;
- el head Alembic no coincide con el repositorio;
- una auditoría no devuelve `PASS`;
- aparece cualquier conflicto de estado, identidad o reconciliación;
- se solicita mutar la versión oficial ya `FROZEN`.

Nunca borrar evidencia ni forzar estados para continuar.
