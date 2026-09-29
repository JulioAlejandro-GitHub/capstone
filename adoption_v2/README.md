> Estado D.3: D-04 resuelta y preflight aprobado. La aplicación se revirtió por FINAL_CATALOG_MISMATCH: D-05 (columna structural_hash generada ausente del contrato objetivo) y D-06 (cuatro CHECK pendientes de equivalencia). Baseline/certificado D-03 no modificados en D.3. Véase docs/audits/e10_10_5_route_b_results.md. Los estados anteriores de este documento son históricos.

# Estado tras D-03 (E10.10.5D.2)

D-01 y D-02 resueltos; el adaptador fija el nuevo manifiesto y catálogo recertificado de Ruta A. La captura usa representación nativa PostgreSQL con `pg_catalog,public` para el esquema legacy, y coteja los 39 bindings/dependencias UUID y la identidad contra el certificado, sin retirar prefijos de expresiones. La comparación final conserva todas las categorías de catálogo, ownership y ACL.

**D continúa bloqueada por `LEGACY_FUNCTION_OWNER_MISMATCH`.** La guarda anterior exige propietario migrador incluso para 36 funciones de pgcrypto que pertenecen a postgres, igual que en Ruta A. No se corrigió esa guarda ni se ejecutó el delta: se requiere decisión D-04. [Informe vigente](../docs/audits/e10_10_5_route_b_results.md).

## Contrato original de C (histórico)

# Adaptador de adopción legacy → PostgreSQL v2

Entrega E10.10.5C: implementación y validación **offline**. Gate B aprobado; Gate C pendiente. El ejecutor existe para el ensayo D y no se ha conectado a ninguna base en C. No es una migración de la baseline vacía ni carga los SQL históricos.

## Componentes

- `core.py`: contrato congelado, hashes, codificación reversible de archivos privados y referencias de evidencia.
- `legacy_contract.json`: forma legacy de E10.10.1, revisión `20260922_01`, PK de 97 tablas y 22 checksums; no incluye filas científicas reales.
- `preflight.py`: esquema, revisiones, checksums, duplicados, gate, actividad y evidencia E10; autorización e identidad de copia aislada.
- `transforms.py` / `planner.py`: plan puro, determinista, sin mutar entradas; configuraciones, evaluaciones, medidas, historia, calibración, consolidación, XAI y reconciliación de relaciones.
- `ddl.py`: delta de adopción a partir del manifiesto certificado; conserva guardas existentes. No ejecuta SQL.
- `execute.py`: futuro ejecutor D con preflight, backup fijado por hash, archivo privado durable, locks, transacción, comparación de catálogo y promoción condicionada de revisión.
- `__main__.py`: comandos explícitos `plan` y `apply`; ninguna conexión por importar el paquete.

Requiere Python 3.11+ y `requirements.txt`. El parser pglast 8.4 utiliza gramática PostgreSQL 18.4: el parseo del delta no sustituye el ensayo PostgreSQL 17.9 de D.

## Plan offline

El snapshot tiene `catalog` (siete grupos estructurales del contrato), `rows` (las 97 tablas), y, al capturarse en D, `native_catalog` y `sequence_values`. Se serializa mediante `core.canonical`; se recupera con `core.decode`. UUID, Decimal, bytes y timestamps tienen etiquetas reversibles. Los diccionarios JSON también se etiquetan para impedir colisiones con payloads originales.

Un archivo de bindings es JSON ordinario con `documents`, `configurations`, `evaluations`, `calibrations`, `consolidations`, `xai` y `xai_excluded`. Las referencias sólo admiten:

```json
{"table":"run_clinical_metrics","key":["UUID existente"],"path":[]}
```

```json
{"document":"contexto_revisado","path":[]}
```

Cada documento contiene `raw` (texto JSON original) y `sha256` (hash de esos bytes UTF-8). Los valores científicos no se aceptan como defaults del adaptador. Un documento es evidencia aportada y revisada, no un mecanismo para inventar datos. El hash del conjunto de bindings debe coincidir con la autorización de D. Los paths sólo navegan campos o índices existentes; una referencia no única o incompleta bloquea.

- `configurations[run_id]`: referencias `canonical` y `sha256`; deben concordar con `execution_parameters.model_configuration_e2.configuration.resolved`.
- `evaluations[]`: `key` estable, referencias `context` y `measurement`, y `members[]` cuando corresponda. El contexto incluye propósito, split, protocolo/población/input/comparison hashes, checkpoint, procedencia y umbral. Toda medición clínica legacy debe quedar cubierta exactamente una vez.
- `calibrations[id]`: referencias `default_evaluation_id` y `selected_evaluation_id`. Las dos evaluaciones deben existir y cumplir el contrato VAL.
- `consolidations[]`: referencia de fila completa `source` y referencia `evaluation_id`; no se agregan mediciones incompatibles.
- `xai[]`: `parent`, `context`, `artifacts[]`. Los valores deben acreditar la cadena de origen. Padres incompletos se conservan y requieren una disposición expresa en `xai_excluded`; no se certifican como nueva evidencia XAI.

Ejemplos ejecutables exclusivamente sintéticos: `tests/adoption_v2/fixtures.py`. No existe un binding preaprobado para la base real.

```sh
python -m adoption_v2 plan --snapshot /ruta/privada/snapshot.json \
  --bindings /ruta/privada/bindings.json --output /ruta/privada/plan.json
```

El directorio de salida debe ser propio, modo 0700 y estar fuera del repositorio. Archivos 0600, creación exclusiva, sin sobrescritura, fsync. El snapshot/plan puede contener credenciales de aplicación; nunca se publica como auditoría pública. Sólo se publican conteos y hashes de reconciliación.

## Ejecutor reservado a D

`apply` requiere descriptor nuevo `E10.10.5D`, Gate C aprobado explícitamente, clúster distinto del origen, Docker/volumen/puerto verificados, roles mínimos, writers aislados y hashes autorizados de backup, esquema, inventario y bindings. Rechaza descriptores B y C. Lee exclusivamente `PGV2_ADOPTION_URL`, sin cargar configuración operativa. `--backup` debe corresponder al backup **de la copia aislada**. El código no crea roles, no restaura backups ni autoriza por sí solo el descriptor.

La captura se realiza después de locks exclusivos sobre las 97 tablas y rechazo de otras sesiones. Se usa READ COMMITTED para no retener un snapshot anterior a la adquisición de locks; una vez adquiridos, el inventario permanece cerrado hasta terminar. Cada sentencia se ejecuta en una única transacción. El archivo privado se sincroniza antes del primer DDL. Se mantienen los 22 registros históricos y se archiva la revisión antigua. `alembic_version` sólo cambia después de validar datos, restricciones y equivalencia de catálogo; no se usa `stamp`.

Una repetición exige `--completed-plan` y su hash en el descriptor; sólo reconcilia y devuelve `already_adopted`, sin aplicar el delta. Debe utilizar un directorio de evidencia nuevo. Un fallo previo a COMMIT revierte DDL/DML/head; conserva el archivo privado para diagnóstico. Una pérdida de conexión durante COMMIT se considera resultado incierto y requiere comprobar identidad, revisión y reconciliación con el plan conservado. Un recibo `prepared` por sí solo no prueba COMMIT.

Ensayos PostgreSQL, recuperación real, backup/restore de adopción y compatibilidad con datos de la copia: **pendientes de D**. No se ejecutó `apply` contra PostgreSQL en C; sus pruebas de transacción usan drivers y conexiones simulados.
