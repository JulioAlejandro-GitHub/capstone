# E10.10.5A — Baseline Alembic v2 y enmienda A-01

## Actualización E10.10.5B — Gate A aprobado; Gate B bloqueado

El usuario aprobó Gate A y autorizó exclusivamente B. Se creó PostgreSQL 17.9 real en un contenedor, volumen y puerto independientes y se registró preflight antes de provisión SQL. El primer CREATE ROLE falló: el contrato usa el prefijo reservado `pg_`. Es un conflicto arquitectónico nuevo y se detuvo la ejecución para solicitar decisión sobre `capstone_v2_migrator` / `capstone_v2_runtime`.

**Ruta A no certificada; Gate B BLOQUEADO.** No se ejecutó Alembic ni se modificó la baseline o el diseño científico. No se iniciaron C/D/E ni cutover. PostgreSQL operativo no recibió conexiones SQL. El contenedor aislado quedó detenido y su volumen se conserva.

Se añadieron `scripts/db/certify_v2_route_a.py`, `docs/audits/e10_10_5b_evidence/`, [resultados Ruta A](e10_10_5_route_a_results.md) y [diff no evaluado](e10_10_5_catalog_diff.json); se actualizaron este informe, tests y riesgos. El runner registra comandos reales y rechaza reutilizar una preparación parcial; no constituye todavía una suite completa de certificación.

La entrega A original se conserva a continuación como registro histórico. Su solicitud de Gate A ya fue satisfecha por la decisión del usuario.

---

Fecha: 2026-09-29.

**A-01 RESUELTA POR DECISIÓN ARQUITECTÓNICA — E10.10.5A PUEDE REANUDARSE.**

**IMPLEMENTACIÓN COMPLETADA — PENDIENTE DE REVISIÓN Y APROBACIÓN.**

Esta entrega cierra el desarrollo y la validación estática de A. **No declara aprobado Gate A ni certificada una instalación PostgreSQL.** B, C, D y E no se han iniciado; ningún gate autoriza cutover.

## 1. Objetivo alcanzado

Se implementó la revisión raíz `pg_v2_baseline`, con `down_revision=None`, en `alembic_v2/`, seleccionada exclusivamente mediante `alembic_v2.ini`. La revisión construye el esquema completo desde recursos SQL propios versionados; no ejecuta los SQL históricos, el DDL conceptual ni `Base.metadata.create_all()`.

El compilador estático forma primero las tablas con columnas/tipos finales, extrae las restricciones inline y ordena claves, funciones, FK, índices, vistas y triggers. Alembic administra `alembic_version`; no se crea dos veces. El entorno implementa DDL transaccional, advisory lock y una guarda de identidad antes de cualquier escritura. No admite stamp, downgrade destructivo ni exportación offline de un instalador sin guarda. Sólo inicializa el gate libre.

### Decisión A-01 y trazabilidad

El usuario aprobó conservar las evaluaciones externas como ámbito científico propio y autorizó reanudar exclusivamente A. El bloqueo inicial se conserva íntegro en [e10_10_5a_initial_block.md](e10_10_5a_initial_block.md); [e10_10_5a_preimplementation_checks.json](e10_10_5a_preimplementation_checks.json) conserva su evidencia original. Esos hashes documentan el estado previo y **no deben confundirse con checksums vigentes después de la enmienda**.

[e10_10_5a_design_before_a01.json](e10_10_5a_design_before_a01.json) registra los hashes originales de los ocho documentos E10.10.4 y la definición original de evaluations. Los documentos afectados incorporan la enmienda sin borrar su decisión histórica. El DDL conceptual conserva la advertencia NO EJECUTAR.

Implementación de A-01:

- `evaluations.split`: `train`, `val`, `test`, `external`; los tres splits oficiales no cambian. `external_validation` permanece sólo en su dominio protegido original, sin alias ni mapping automático.
- Finalidad externa exclusiva `complementary`, rol `external_complementary`. External no puede tomar roles de VALIDATION, TEST, desarrollo o calibración.
- Población: hash y manifiesto recuperable con SHA-256. Procedencia: `dataset_origin_id`, `dataset_origin_role`, URI y SHA-256 de evidencia. Protocolo: versión, hash y snapshot independientes. No se completa ninguno desde nombres de archivo o etiquetas.
- FK de procedencia a la PK existente `(dataset_version_id,dataset_id,role)` de `dataset_version_sources`, sin modificar el dominio protegido. La versión externa evaluada puede diferir de la usada por TRAIN; se conservan TRAIN, modelo y checkpoint y la coherencia del ensemble respecto de su TRAIN de referencia.
- Nuevas entradas trazadas usan `source_kind=external_record`; adopción histórica usa `legacy` sólo con evidencia suficiente. No se etiquetan artificialmente como E10 ni como assessment oficial.
- `run_clinical_metrics` conserva `split_name=external` al derivarlo de la evaluación. El par de calibración sigue exigiendo `val`. `vw_v2_model_comparison` excluye external; `vw_v2_external_evidence` expone evidencia complementaria con población/procedencia/protocolo sin agregación al TEST oficial.
- Los escritores y lectores legacy operativos permanecen sin cambios. Su adaptación transaccional a las columnas obligatorias v2 y la exclusión en selección/API/React corresponden a E. No se afirma que un INSERT legacy sin evaluation_id funcione directamente sobre v2.

### Inventario implementado

| Objeto | Cantidad |
| --- | ---: |
| Tablas de aplicación | 102 |
| Tabla de versión administrada por Alembic | 1 |
| Total de tablas físicas previsto | **103** |
| Vistas | **33** |
| Funciones propias | 75 |
| Triggers de aplicación, incluidos constraint triggers | 95 |
| PK aplicación / UNIQUE / CHECK / FK | 102 / 75 / 524 / 249 |
| Índices independientes | 229 |
| Secuencias propias | 1 |
| Extensión adicional | pgcrypto |

Las PK/UNIQUE crean sus índices propios; no se emiten duplicados. `plpgsql` es un prerrequisito incorporado. Los triggers RI y objetos internos de extensiones son administrados por PostgreSQL. Se añade la PK/índice de Alembic a los conteos de aplicación.

Inventario nominal completo: [e10_10_5a_object_inventory.md](e10_10_5a_object_inventory.md). Definiciones y propiedades verificables: [catalog_manifest.json](../../alembic_v2/baseline/catalog_manifest.json).

## 2. Archivos creados o modificados

**Implementación nueva:**

- `alembic_v2.ini`.
- `alembic_v2/{__init__.py,env.py,safety.py,resources.py,README.md,requirements.txt,requirements-static.txt}`.
- `alembic_v2/versions/20260929_01_pg_v2_baseline.py`.
- `alembic_v2/baseline/01_prerequisites.sql` a `11_technical_state.sql`, y `catalog_manifest.json`.
- `scripts/db/{build_v2_baseline.py,validate_v2_static.py,check_v2_stage_a.py}`.
- `tests/db_v2/{test_static_baseline.py,test_alembic_envelope.py}`.

**Diseño actualizado por A-01:** los ocho archivos `docs/audits/e10_10_4_{postgresql_v2_architecture.md,schema_matrix.csv,jsonb_normalization.md,target_schema.sql,er_diagram.md,alembic_strategy.md,dependency_matrix.md,implementation_plan.md}`. Ya estaban no rastreados al inicio: no se presentan como creaciones de esta etapa.

**Evidencia:** este informe, `e10_10_5_test_results.md`, `e10_10_5_open_risks.md`, y los archivos `e10_10_5a_{initial_block.md,design_before_a01.json,history_manifest.json,static_results.json,commands.json,object_inventory.md}`. El archivo previo `e10_10_5a_preimplementation_checks.json` se conserva sin reescribirlo.

No se modificaron código de aplicación, `execution/schema.py`, Alembic operativo, SQL históricos ni configuración de servicios.

## 3. Comandos realmente ejecutados

Registro exacto de la validación final, con argv, códigos de salida y stdout/stderr: [e10_10_5a_commands.json](e10_10_5a_commands.json).

Comando integral ejecutado desde la raíz:

```sh
PYTHONPATH=/tmp/e10_10_4_sql_parser:. python3 scripts/db/check_v2_stage_a.py --alembic-python malaria_dl_local_project/.venv/bin/python
```

El runner ejecutó nueve comandos: `build_v2_baseline.py --check`; `validate_v2_static.py --report ...`; dos suites unittest separadas; `alembic -c alembic_v2.ini heads`; `history`; `ruff check`; `ruff format --check`; compilación Python en memoria.

Durante desarrollo también se ejecutaron `build_v2_baseline.py --write`, las suites y validaciones individualmente, `ruff check --fix --unsafe-fixes` y `ruff format` sobre archivos nuevos, inspecciones de archivos con `rg`, `cat`, `sed`, `head`, `ls`, `find`, `git status --short`, `git diff --stat` y scripts Python locales para snapshots de diseño/historia e inventario. Se volvió a ejecutar el verificador estático previo `/tmp/e10_10_4_check.py`; sólo analiza archivos.

No se ejecutó `alembic upgrade`, `downgrade`, `stamp`, `psql`, Docker, pg_dump, pg_restore ni ningún comando de entrenamiento/evaluación. Los tests invocaron guardas del entorno/revisión con conexiones ausentes o rechazadas, no una migración.

## 4. Pruebas aprobadas, fallidas y omitidas

- **24/24 pruebas aprobadas** en las suites finales seleccionadas: 19 estáticas de catálogo/A-01/seguridad y 5 de control del entorno Alembic.
- **9/9 comandos finales aprobados**, sin tests omitidos dentro de esas suites.
- **72 cuerpos PL/pgSQL** pasan análisis sintáctico; funciones LANGUAGE sql también analizadas.
- Conservados por comparación independiente contra E10.10.1: **65 funciones**, **77 triggers**, **780 restricciones**, **225 índices independientes** y **27 vistas** legacy.
- **17 tablas protegidas** contrastadas con el diseño; **54 archivos históricos** intactos y **22 checksums** coincidentes con el ledger capturado. `004_seed.sql` sigue excluido.
- Se rechazaron mediante pruebas estáticas los casos de FK sin target único, función de trigger ausente, recurso alterado, identidad de clúster/base incorrecta, rol privilegiado, volumen compartido, bind mount y puerto no exclusivo.

Las incidencias iniciales de normalización del parser, una prueba negativa que confundía índice con constraint, un descriptor CSV y lint se corrigieron; se detallan en [resultados](e10_10_5_test_results.md). **Fallos finales pendientes: ninguno en A.**

**Omitido por alcance:** toda prueba real de PostgreSQL, instalación, catálogo observado, rollback, idempotencia, backup/restore, adopción y contratos funcionales. Estas pruebas no se sustituyeron por mocks ni se declararon aprobadas.

## 5. Evidencia reproducible y rutas

- [Comandos ejecutados y salidas](e10_10_5a_commands.json).
- [Resultado estructural estático](e10_10_5a_static_results.json).
- [Inventario completo](e10_10_5a_object_inventory.md).
- [Manifiesto de historia inmutable](e10_10_5a_history_manifest.json).
- [Definiciones objetivo congeladas](../../alembic_v2/baseline/catalog_manifest.json).
- [Procedimiento y prerrequisitos](../../alembic_v2/README.md).

El manifiesto da ubicación por bytes y SHA-256 de cada sentencia, además de columnas con tipo/default/nulabilidad/expresión generada/colación. `--check` reproduce exactamente los recursos; el validador comprueba orden y targets FK, cuerpos/triggers heredados, CHECK, índices, vistas y fuentes históricas sin conectarse a una base.

Intérpretes usados: Python 3.14 para pglast 8.4 (parser PostgreSQL **18.4**); entorno Python 3.12 existente para Alembic 1.18.5 / SQLAlchemy 2.0.51 / psycopg 3.3.4. La baseline apunta a PostgreSQL **17**, todavía no ensayado. La ruta local `/tmp/e10_10_4_sql_parser` no es dependencia de instalación: las dependencias de revisión están declaradas para reproducirlo en otro entorno.

## 6. Diferencias frente a E10.10.4

1. **A-01 aprobada:** external complementario, seis columnas de población/procedencia, una FK adicional y una vista adicional. Resultado: 103 tablas, **33** vistas y **249** FK. Se conserva external_validation sin transformación.
2. Alembic crea su tabla/PK; la baseline emite 102 tablas de aplicación y no duplica alembic_version.
3. Se materializan de entrada columnas/tipos finales. Se elimina el orden conceptual «vistas antiguas → ALTER TYPE», que no es adecuado para una instalación vacía ordenada.
4. Se extraen las restricciones inline y se les asignan nombres explícitos deterministas donde el diseño no fijaba nombre; se conservan los nombres históricos. Los índices UNIQUE completos preceden a las FK que los requieren.
5. Funciones y vistas se ordenan por dependencias. Se usa `check_function_bodies=true` desde el principio; no se usa la desactivación global conceptual. Los 65 cuerpos legacy y sus opciones siguen conservados.
6. Permisos concretos de instalación aislada: migrador owner y runtime separado, sin DDL/TEMP/TRUNCATE/roles administrativos; runtime no escribe ledgers. No se inventan equivalencias con ACL operativos no acreditados. La revisión no crea roles del clúster.
7. Guarda de identidad del contenedor/volumen/puerto y del servidor/clúster/base/roles; rechazo de destinos legacy, parciales o ambiguos antes de cualquier escritura. No basta una variable de entorno o un nombre de base.
8. El gate libre se inserta una sola vez en la revisión; no se siembran datos científicos ni los 22 registros históricos.

No se alteró la regla de publicación TRAIN/EVALUATE ni los hashes/eventos E10. La elegibilidad, el protocolo de selección y las lecturas funcionales se certificarán en E.

## 7. Riesgos pendientes

[Riesgos completos](e10_10_5_open_risks.md). En particular:

- Validación estática con parser 18.4 no equivale a compilación/ejecución en PostgreSQL 17.
- Roles, ACL, extensión pgcrypto, identidad real y transacciones deben ensayarse en B; el administrador aislado deberá conceder al migrador la lectura de `pg_control_system()`.
- No se ha demostrado aún rollback, no-op de segunda ejecución, backup/restore ni igualdad de catálogo real.
- La evidencia histórica sólo acredita la captura previa; C/D deberán recensear la copia autorizada y reconciliar datos/typmods/colaciones sin inventar valores.
- URI/hash no certifica contenido ni disponibilidad. Las políticas de selección, la exclusión externa en servicios/UI y la adaptación de escritores se prueban en E.
- El runtime legacy continuará rechazando el head v2 hasta la adaptación explícita de capacidades en E; no se desactivó su guarda.

## 8. PostgreSQL operativo permanece intacto

**Confirmación explícita: PostgreSQL operativo permanece intacto por las acciones de esta entrega.** No se abrió ninguna conexión PostgreSQL ni se ejecutó Docker, DDL/DML, migración, stamp, backup/restore o workflow científico. No se leyeron imágenes ni se recalcularon sus checksums. No se modificaron usuarios, credenciales, modelos, dataset, rutas, splits, procesos, campañas, sesiones o gate operativos.

Los hashes calculados corresponden a archivos locales de diseño/código/migraciones. La confirmación describe las acciones de esta sesión; no se presenta como una nueva medición del estado operativo ni de actividad externa.

## 9. Decisión solicitada — Gate A

Se solicita revisión de esta entrega y **aprobación explícita para iniciar E10.10.5B: instalación y certificación de Ruta A en PostgreSQL 17 vacío y aislado**, con identidad acreditada antes de escribir.

La ejecución se detiene aquí. No se inicia B automáticamente. La aprobación de Gate A no autoriza C, adopción legacy, cambios operativos ni cutover.
