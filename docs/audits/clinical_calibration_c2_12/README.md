# C2.12 — Diagnóstico de integración y bloqueo de aislamiento

Estado documental: `HISTORICAL_AUDIT`. Fecha: 2026-10-04.
Resultado: **BLOQUEADO**. No constituye aprobación de integración PostgreSQL.

## Actualización C2.12.1 — base desechable en la misma instancia

Resultado: **BLOQUEADO antes de provisionar**. Se revisó la alternativa de base
desechable autorizada por el usuario. El impedimento ya no es falta de autoridad
administrativa: el administrador configurado `julio` tiene `rolsuper=true` y por
ello puede crear bases aunque su atributo `rolcreatedb` sea false. Se comprobó
mediante SQL real en una transacción READ ONLY del servicio Compose `db`.
Los roles migrator/runtime siguen sin superuser, CREATEDB ni CREATEROLE.

El impedimento concreto está en el instalador vigente, no en PostgreSQL:

| Control existente | Instancia actual / resultado |
|---|---|
| alembic_v2/safety.py: read_authorization | Admite sólo E10.10.5B, E10.10.5E, DBV2.2 y DBV2.3 con sus aprobaciones históricas; no C2.12.1 |
| Puerto de destino admitido | Prohíbe 5432 y 5433; Compose publica 127.0.0.1:5432 |
| validate_docker_snapshot | Exige etiqueta org.capstone.pgv2.isolation; el contenedor Compose actual no la tiene |
| alembic_v2/env.py | Exige estos controles antes de ejecutar la revisión; no admite conexión externa |
| Resultado de las funciones reales, sin cambios | V2_AUTHORIZATION_MISMATCH y V2_CONTAINER_LABEL_MISMATCH |

Estos rechazos se reprodujeron llamando las funciones puras de seguridad con
metadata Docker real y un descriptor candidato explícitamente C2.12.1. No se
ejecutó Alembic ni se presentó una aprobación histórica como si fuera actual.
La falta de OID de una base nueva es deliberada: no se creó una base que el
instalador no pudiera aceptar. El puerto y la etiqueta son incompatibilidades
independientes confirmadas en código y metadata.

Los precedentes scripts/db/verify_v2_route_a.py y
scripts/db/test_v2_d04_operations.py crean bases hijas, pero parten de un target
histórico certificado y verifican inspect_isolation. No habilitan una ruta
actual para esta instancia Compose. Los scripts de recertificación crean
contenedores/roles y no cumplen las restricciones de esta tarea. El baseline
inmutable dispone de load_baseline(), pero ejecutar sus SQL directamente o
marcar pg_v2_verified_target manualmente eludiría la verificación del instalador;
no se hizo. Tampoco se clonó la base operativa con sus datos históricos.

**Alternativa mínima viable:** autorizar un cambio acotado del control de
aprovisionamiento/identidad en alembic_v2/safety.py para reconocer una base
desechable C2.12.1 dentro del Compose existente. Debe validar container ID,
system identifier, OID, nombre aleatorio y propietario migrator; excluir la base
operativa y exigir base vacía. El administrador existente crearía/eliminaría
exclusivamente ese destino; no hacen falta nuevos privilegios. El instalador
seguiría siendo `alembic -c alembic_v2.ini upgrade head`. Los guards científicos,
triggers y constraints permanecerían íntegros. La eliminación exigiría identidad
coincidente y cero conexiones ajenas, sin DROP FORCE ni terminar sesiones ajenas.
Esta alternativa **requiere modificar un guard de aprovisionamiento**, prohibido
por la restricción actual de no modificar guards para permitir pruebas; se
presenta para una decisión posterior y no está implementada ni autorizada por
inferencia. No se necesita otra instancia ni infraestructura permanente.

Evidencia reproducible:

- `make check-calibration-database-isolation`: código **2**, diagnóstico de solo
  lectura en [database_isolation_preflight.txt](database_isolation_preflight.txt).
- Nueva ejecución de `make test-scientific-parameters`: salida en
  [scientific_regression_c2121.txt](scientific_regression_c2121.txt).
- `make test-calibration-postgres` conserva su preflight bloqueante de C2.12;
  **no se convirtió en una suite E2E ni debe interpretarse como tal**.

No se crearon bases, filas, roles ni artefactos de entrenamiento. El inventario
de bases no template sólo contiene malaria_experiments (OID 16386) y postgres
(OID 5). No hay bases desechables de esta ejecución que destruir. La base
operativa permanece sin escrituras de este trabajo; no se afirma una comparación
bit a bit ni ausencia de actividad de otros clientes. No se accedió a TEST ni a
contenido histórico. Los únicos cambios son diagnóstico, objetivo Makefile y
documentación. La fixture, persistencia E2E, idempotencia, conflictos, fallo SQL
y limpieza de una base realmente creada **siguen pendientes**. C2.12 no aprobado.

## Evidencia ejecutada

Se consultó la instancia Docker existente, sin crear otra instancia. La evidencia
literal sanitizada está en [postgres_preflight.txt](postgres_preflight.txt).
`make test-calibration-postgres` terminó con código **2**, antes de escrituras.
PostgreSQL informa 17.9, esquema public, revisión pg_v2_baseline y transacción
read_only=on. `require_e10_schema()` acredita columnas, CHECK, índices únicos y
trigger de eventos vigentes. Las ocho tablas solicitadas existen.

`make test-scientific-parameters`: **87 passed, 2 warnings in 13.60s**; código 0.
Las dos advertencias son deprecaciones de metaclases protobuf para Python 3.14.
No hay pruebas fallidas en esa regresión. Pruebas C2.12 de escritura PostgreSQL:
**0 ejecutadas**; idempotencia, fallo SQL y comparación de RUN persistidos quedan
sin acreditar. Las consultas de prerrequisitos no se cuentan como pruebas E2E.

## Por qué se detuvo

1. `PostgresResultRepository.acceptance_scope()` abre una conexión nueva y confirma
   una transacción raíz por evento. Rechaza una transacción externa. Sustituirla
   por savepoints para la prueba eliminaría precisamente la garantía a verificar.
2. El rol configurado devuelve `has_database_privilege(...,'CREATE') = false`.
3. `experiment_require_owner()` tiene `search_path=public, pg_catalog`. Cambiar
   solamente el search_path de una conexión no aísla el control de propietario.
4. Las fixtures de `test_result_repository_postgres.py` reutilizan migraciones
   legacy y esquemas temporales; no son una fixture certificada del baseline v2
   actual. No se ejecutaron ni se adaptaron mediante desactivación de guards.

El gate estaba libre, pero eso no autoriza ocuparlo ni convertir el entorno
operativo en una fixture. Se aplicó la regla explícita del encargo: detener la
prueba cuando no pueda garantizarse aislamiento. No se ampliaron privilegios,
modificaron funciones ni ejecutaron migraciones. No es un fallo científico ni
una demostración de defecto de idempotencia.

## Inventario de integración inspeccionado

Rutas bajo `malaria_dl_local_project/src/malaria_dl/`:

| Componente | Implementación y recorrido identificado |
|---|---|
| Registro científico | models/scientific_parameters.py: effective_values, compare_runs; 73 entradas, sin rellenar históricos |
| Contratos y matriz | campaigns/contracts.py: expand_matrix; protocolo traduce calibration.algorithm y restricciones clínicas |
| Campaña | campaigns/repository.py: create_frozen, _materialize; requested/protocol/contract y configuraciones por hash |
| RUN | execution/repository.py: claim, _create_run; snapshot con semilla y project_configuration |
| TRAIN sintético | execution/train.py: selección, CalibrationController, evaluación final; probado con dobles en regresión |
| Controlador | evaluation/calibration_controller.py: calibrate, threshold; delega al buscador existente |
| Eventos | execution/emitter.py: RunEventEmitter; reporters/docker.py y reporters/http.py; contrato RunReporter |
| Aceptación | results/service.py: accept_event; igualdad canónica, conflictos de identidad/secuencia y proyección atómica |
| Adaptador SQL | persistence/result_repository.py: PostgresResultRepository; autorización, ledger y commit propio |
| Proyecciones | persistence/v2_projection.py: project_configuration, project_calibration, project_evaluation |
| Contexto | execution/repository.py: bind_evaluation_context; checkpoint, protocolo, población e input contract |

Relaciones identificadas en código y esquema, sin crear filas para verificarlas:

| Tabla | Linaje / evidencia |
|---|---|
| experimental_campaigns | requested, protocol, contract, contract_hash |
| campaign_configurations | campaign_id + configuration_hash; configuration y requests |
| campaign_members / campaign_attempts | miembro y semilla → intento → training_run_id |
| runs | campaign_id, dataset_version_id, execution_parameters con snapshot de configuración |
| run_configurations | run_id; extension_configuration efectivo, provenance_snapshot íntegro, configuration_hash |
| train_execution_sessions | run_id, attempt_id, owner y configuración autorizada |
| train_execution_records | run_id; registros TRAIN y eventos por event_id/event_sequence, canonical_event completo |
| artifacts | checkpoint_artifact_id de evaluación; metadata de época |
| evaluations | training_run_id, dataset_version_id, checkpoint, protocolo/población/input hashes, threshold_used/source |
| run_threshold_calibration | run_id, default_evaluation_id y selected_evaluation_id |
| run_clinical_metrics | evaluation_id; conteos y métricas derivadas por trigger |

`run_configurations.configuration` no existe: usar extension_configuration.
El hash de configuración de miembro no debe confundirse con el hash efectivo
del RUN que incluye su semilla.

## Escenarios y límites de la evidencia

La regresión existente ejercita A (desactivado, 0.5, sin invocar buscador ni emitir
CALIBRATION_COMPLETED), B (activado, etiquetas [0,1], scores [.1,.9], target .98)
y C (etiquetas [0,1], scores [.8,.2], min_specificity=1). Compara el controlador
con el buscador original, incluidos flags y advertencias; excluye únicamente
created_at de llamadas independientes. TRAIN usa dobles científicos, no entrena
modelos reales. Sus datasets simulados son TRAIN y VAL.

La regresión también verifica parámetros ausentes/desconocidos sin defaults,
configuración inválida y ausencia de mutación de snapshots. Estas verificaciones
son unitarias: no demuestran ida y vuelta de campañas ni snapshots en PostgreSQL.
No se crearon RUN A/B persistidos, ni evidencia de eventos SQL sintéticos. No se
declaran equivalentes experimentos por coincidencia de parámetros: hacen falta
datos, linaje y entorno además del snapshot.

Se revisaron docs/scientific_parameters.md y la auditoría clinical_threshold_c1.
H01 conserva relajación de especificidad; H02 conserva >= en TRAIN y > en E7;
H03 conserva completion con selección a 0.5; H04 conserva el detalle en eventos
frente a resúmenes incompletos; H05 conserva la validación numérica histórica.
Ningún algoritmo, fallback, contrato o política fue modificado.

En particular, project_calibration conserva warning, candidate_count y flags en
el evento/registro completo, pero omite esos campos en la proyección resumida.
Un NULL en esa tabla no significa false. Las métricas de selección, evaluación
final VAL, calibración y cumplimiento clínico continúan siendo conceptos distintos.

## Reproducción y SQL

Ejecutar `make test-calibration-postgres`. El objetivo actual es un **preflight
bloqueante**, no la suite E2E terminada. Su SQL está íntegro en
scripts/check_calibration_postgres.py y reutiliza read_only_transaction y
require_e10_schema. No devuelve éxito aunque cambien permisos: primero debe
implementarse y acreditarse una fixture v2 aislada que cubra commits independientes.
El error de conexión/esquema también devuelve salida no exitosa.

Consultas pendientes para la futura fixture (no ejecutadas sobre históricos):

```sql
SELECT r.id, r.campaign_id, rc.configuration_hash,
       rc.extension_configuration, rc.provenance_snapshot
FROM runs r JOIN run_configurations rc ON rc.run_id=r.id
WHERE r.campaign_id=:synthetic_campaign_id;

SELECT event_id, event_sequence, payload FROM train_execution_records
WHERE run_id=:synthetic_run_id ORDER BY event_sequence;

SELECT e.evaluation_role, e.threshold_used, e.threshold_source,
       e.checkpoint_artifact_id, m.tn, m.fp, m.fn, m.tp
FROM evaluations e JOIN run_clinical_metrics m ON m.evaluation_id=e.id
WHERE e.training_run_id=:synthetic_run_id AND e.split='val';
```

## Estado final y próximos pasos

No se emitió DML/DDL ni se crearon objetos/filas; no hubo limpieza destructiva.
La consulta final no encontró esquemas capstone_test_*. La transacción de lectura
se cierra con rollback. B1 no fue modificado por este trabajo; esta afirmación se
basa en ausencia de escrituras, no en una comparación de contenido histórico.
No se leyó TEST, imágenes, scores históricos ni el subsistema cerrado de datasets.
No se ejecutaron campañas, entrenamientos reales ni recalibraciones históricas.

Cambios: objetivo Makefile, script de prerrequisitos y esta evidencia/indexación.
La regresión científica conserva su comando y comportamiento. No hubo cambios
en código productivo ni frontend.

Pendiente: mecanismo autorizado de esquema temporal v2 que preserve todos los
guards y referencias, aislamiento de commits, limpieza exclusiva y comprobación
independiente de residuos. Después: campaña/matriz → dos RUN → eventos y SQL,
duplicado/conflicto/secuencia/fallo SQL, snapshots y comparación. Los once
criterios de aceptación conjuntos siguen sin acreditarse.

**Recomendación:** no usar C2.12 como autorización para la campaña mini CPU/GPU.
Completar primero la verificación aislada; conservar calibración pública `none`.
