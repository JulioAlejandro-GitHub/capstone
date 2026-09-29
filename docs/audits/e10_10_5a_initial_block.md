# E10.10.5A — Bloqueo durante la revisión previa

Fecha: 2026-09-29. **BLOQUEADA — IMPLEMENTACIÓN NO COMPLETADA.**

No corresponde utilizar «IMPLEMENTACIÓN COMPLETADA — PENDIENTE DE REVISIÓN Y APROBACIÓN»: todavía no existe una baseline implementada. Ningún gate está aprobado. B–E no se han iniciado.

## 1. Objetivo alcanzado

Se identificó una incompatibilidad entre el dominio científico conservado y el nuevo dominio de evaluaciones, antes de modificar código o ejecutar PostgreSQL. La revisión integral previa permanece pendiente; este informe no constituye una auditoría exhaustiva de todos los objetos del DDL.

**Conflicto A-01: continuidad de resultados externos.**

| Evidencia | Localizador | Consecuencia |
| --- | --- | --- |
| Las métricas actuales admiten `external` | `e10_10_4_target_schema.sql:4947`, `chk_run_clinical_metrics_split` | Es parte del dominio conservado. |
| Las asignaciones protegidas admiten `external_validation` | mismo archivo:4647 | Existe también una categoría externa en el dataset; no se demuestra que sea equivalente a `external`. |
| Las evaluaciones nuevas sólo admiten `train`, `val`, `test` | mismo archivo:7604 | No existe identidad de evaluación externa en v2. |
| Toda métrica requiere `evaluation_id` | mismo archivo:7662 | No puede conservarse una métrica externa simplemente omitiendo su evaluación. |
| El trigger impone `NEW.split_name := e.split` | función `v2_binary_metric_guard`, mismo archivo | No sirve conservar el CHECK antiguo: la proyección sustituye el split por el de la evaluación. |
| El lector actual considera explícitamente `external` | `backend_api/app/routes/runs.py:348` | La categoría no aparece sólo en un comentario de diseño. |
| El escritor transmite `split_name` a la tabla métrica | `malaria_dl_local_project/src/malaria_dl/persistence/run_repository.py:1153` | Debe resolverse el contrato de escritura al adaptar v2. |

La normalización E10.10.4 §4 permite archivar evidencia no mapeable y marcarla como no comparable. Eso ofrece una salida para evidencia histórica incompatible, pero no define si se retira o conserva la capacidad de representar nuevas evaluaciones externas. No se afirma que existan filas externas actualmente: no se consultó la base.

**Propuesta para revisión:** conservar un ámbito externo explícito, separado de TRAIN/VALIDATION/TEST, con población y protocolo propios. Su nombre, propósito, roles de evaluación y procedencias admitidas deben quedar definidos antes de incorporar los CHECK correspondientes. No convertir automáticamente `external` ni `external_validation` a `val` o `test`, ni permitir que esa extensión habilite selección/calibración. La correspondencia entre las dos etiquetas externas requiere evidencia de procedencia; no se presupone.

La alternativa es aprobar expresamente que v2 sólo admita las tres poblaciones actuales, retirando la escritura externa y especificando cómo seguirá disponible la evidencia histórica archivada. Es una decisión de alcance, no una corrección de orden de dependencias.

## 2. Archivos creados o modificados

Sólo se crearon:

- `docs/audits/e10_10_5_implementation.md`: este informe de bloqueo.
- `docs/audits/e10_10_5a_preimplementation_checks.json`: seis comprobaciones textuales y hashes de sus fuentes.

Código desarrollado y objetos implementados: **ninguno**. No se creó una revisión vacía ni un manifiesto que aparentara describir un catálogo instalado. Los ocho documentos E10.10.4 ya aparecían como archivos no rastreados al inicio; no fueron creados ni modificados en esta ejecución.

## 3. Comandos realmente ejecutados

Se ejecutaron inspecciones locales con `pwd`, `ls -la`, `find .. -name AGENTS.md -print`, `git status --short`, `rg`, `wc -l`, `cat`, `sed`, `head`, `tail` y `command -v python3`. Entre las consultas directamente relacionadas con el hallazgo:

```sh
rg -n 'chk_run_clinical_metrics_split|chk_dataset_split_assignments_split|CREATE TABLE public.run_clinical_metrics' docs/audits/e10_10_4_target_schema.sql
sed -n '1140,1205p' malaria_dl_local_project/src/malaria_dl/persistence/run_repository.py
sed -n '330,352p' backend_api/app/routes/runs.py
sed -n '90,125p' docs/audits/e10_10_4_jsonb_normalization.md
```

Se ejecutó además `python3` mediante heredoc, utilizando exclusivamente `pathlib`, `hashlib`, `json` y `re`: leyó las fuentes locales, verificó las seis condiciones y escribió el JSON de evidencia con creación exclusiva (`open('x')`). Terminó con código 0. Los SHA-256 corresponden a archivos de texto de diseño/código, no a imágenes, credenciales ni datos científicos.

## 4. Pruebas aprobadas, fallidas y omitidas

- **Comprobaciones estáticas satisfechas:** 6/6 condiciones que demuestran el conflicto; véase JSON. Esto no significa que la baseline pase una prueba.
- **Compatibilidad pendiente:** el dominio externo conservado no tiene representación en `evaluations.split`. No se ejecutó un INSERT para demostrar rechazo en PostgreSQL.
- **Pruebas ejecutables fallidas:** ninguna, porque no se ejecutaron pruebas de aplicación o base de datos.
- **Omitidas por detención:** validación estática integral de la baseline, instalación, catálogo real, funciones/triggers, rollback, idempotencia, backup/restore, adopción y recorrido funcional.

## 5. Evidencia reproducible

Informe: este archivo. Evidencia: [e10_10_5a_preimplementation_checks.json](e10_10_5a_preimplementation_checks.json).

La siguiente comprobación reproduce las seis condiciones y verifica que las fuentes no cambiaron respecto de la captura. No abre conexiones ni escribe archivos:

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib, json, re
evidence = json.loads(Path('docs/audits/e10_10_5a_preimplementation_checks.json').read_text())
for source in evidence['sources']:
    assert hashlib.sha256(Path(source['path']).read_bytes()).hexdigest() == source['sha256'], source['path']
sql = Path('docs/audits/e10_10_4_target_schema.sql').read_text()
start = sql.index('CREATE TABLE public.evaluations (')
evaluation = sql[start:sql.index('\n);', start)]
checks = [
    bool(re.search(r"ADD CONSTRAINT chk_run_clinical_metrics_split[^\n]*'external'", sql)),
    bool(re.search(r"ADD CONSTRAINT chk_dataset_split_assignments_split[^\n]*'external_validation'", sql)),
    "split text NOT NULL CHECK(split IN ('train','val','test'))" in evaluation,
    'ADD COLUMN evaluation_id uuid NOT NULL UNIQUE' in sql,
    'NEW.split_name:=e.split;' in sql,
    "rcm.split_name IN ('test', 'external')" in Path('backend_api/app/routes/runs.py').read_text(),
]
assert all(checks), checks
print('6/6 condiciones reproducidas; fuentes sin cambios; conflicto pendiente')
PY
```

## 6. Diferencias frente a E10.10.4

Ningún cambio aplicado al diseño. Se propone resolver explícitamente A-01 antes de fijar el catálogo ejecutable. No se modificaron tipos, objetos, migraciones, contratos ni configuración de Alembic.

## 7. Riesgos pendientes

- Convertir una población externa a VALIDATION o TEST alteraría su significado científico.
- Conservar sólo el CHECK legacy produciría una falsa impresión de compatibilidad: la evaluación obligatoria y el trigger impiden mantener `external` en la proyección tipada.
- El número actual de filas y su procedencia son desconocidos. La captura histórica no acredita que sigan vacías.
- Resta completar la lectura/revisión integral requerida, resolver dependencias y verificar la baseline. Este hallazgo no acredita ausencia de otros conflictos.
- La identidad aislada, los permisos, los typmods y el catálogo real aún no están certificados.

## 8. PostgreSQL operativo

**PostgreSQL operativo permanece intacto por esta ejecución.** No se abrió conexión PostgreSQL, no se inició Docker, no se ejecutó DDL/DML, Alembic, stamp, backup/restore ni tareas científicas. Tampoco se modificaron SQL históricos, dataset, modelos o usuarios. Esta confirmación describe las acciones de esta sesión; no es una medición del estado de procesos externos.

## 9. Decisión solicitada

Resolver A-01: ¿conservar en v2 un ámbito externo explícito mediante una enmienda revisable del diseño, o retirar expresamente esa capacidad y definir la consulta de su evidencia histórica?

Se recomienda conservar el ámbito externo. La decisión permite reanudar **A**, no iniciar B. **Gate A aún no se solicita:** corresponde únicamente después de entregar la baseline y sus validaciones estáticas. Ninguna aprobación de diseño ni de gate autoriza el cutover operativo.
