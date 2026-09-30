# E10.10.5E.3 — E-03 aplicada a candidata; recertificación bloqueada por E-04

**Integración incompleta. Candidata no certificada. Gate E bloqueado y no solicitado.**

## Cambio autorizado implementado

El generador sustituye exactamente un CHECK de `evaluations`: para `source_kind='e10'` admite exclusivamente `training_validation_final`, `calibration_default` y `calibration_selected`. Se regeneraron SQL y manifiesto con hashes propios; la especificación histórica no se editó. La nueva restricción se llama `v2_evaluations_check_28938a6edbaa`, por su contenido.

El cambio de roles es una candidata instalada en un PostgreSQL 17.9 nuevo y aislado. **No se promovieron los pins `MANIFEST_HASH`/`CATALOG_HASH` de adopción ni el certificado anterior.** Esos pins conservan E.1 y rechazarán la candidata hasta que exista una recertificación completa. No usar este árbol para una instalación aprobada, adopción o cutover mientras continúe el bloqueo.

## Evidencia ejecutada

- [Descriptor aislado](e10_10_5e3_evidence/route_a/target.json): contenedor `capstone_v2_isolated_d0ffe22fab83`, puerto local `55494`, PostgreSQL `17.9`, system identifier `7691305878736203818`. Volumen, base y credenciales nuevos; no se cargó `.env` operativo.
- Instalación desde cero y comparación canónica de catálogo aprobadas. [Comparación](e10_10_5e3_evidence/route_a/catalog_diff.json) y [delta exacto contra E.1](e10_10_5e3_evidence/route_a/candidate_status.json): únicamente cambió el CHECK de roles. Igualdad de catálogo no acredita los invariantes científicos.
- [30 pruebas estáticas aprobadas](e10_10_5e3_evidence/static_tests.txt), incluida la lista exacta de roles y preservación de los demás SQL. `build_v2_baseline.py --check` reproduce los 12 recursos.
- [Diagnóstico PostgreSQL](e10_10_5e3_evidence/route_a/e03_contract_diagnostic.json): 20 casos, un control SQL admitido, 11 rechazos esperados y ocho rechazos ausentes. El proceso termina en **1**, deliberadamente: no es una suite aprobada.
- Cada caso fuerza `SET CONSTRAINTS ALL IMMEDIATE` y revierte su transacción. Se comprobaron cero runs, eventos, evaluaciones, métricas y calibraciones al terminar. Los casos admitidos indebidamente tampoco permanecen persistidos.
- [Preservación histórica](e10_10_5e3_evidence/historical_preservation.json): 149 archivos D.4/E.1/E.2 y especificación original iguales a Git HEAD. No se reescribieron eventos ni hashes históricos.

Los padres, eventos, métricas y procedencia del diagnóstico son **fixtures sintéticos declarados**. `valid_pair` significa control estructural SQL; no acredita un productor TRAIN ni evidencia científica procedente de una ejecución. La identidad UUID5 y las claves discriminadas por rol del fixture no son una implementación del proyector runtime ni una prueba de idempotencia del servicio. El `canonical_event` de cada caso aceptado por SQL se comprobó sin cambios.

## E-04 — el contrato de calibración no garantiza sus invariantes

La autorización dice «Modificar exclusivamente el contrato que actualmente restringe» los roles de origen E10; el apartado 11 ordena detenerse ante otra incompatibilidad arquitectónica. El CHECK autorizado se amplió. Aparece un problema distinto: las guardas existentes permiten hechos que los apartados 3 y 6 obligan a rechazar. Para corregirlo hay que cambiar admisión, integridad referencial de la pareja y unicidad, además del CHECK de roles.

| Caso inválido aceptado por PostgreSQL | Causa confirmada en el contrato |
|---|---|
| Protocolo incompatible entre default/selected | `v2_calibration_pair_guard` no compara protocolo, versión ni snapshot |
| Contrato de entrada incompatible | La guarda no compara `input_contract_hash` |
| selected sin procedencia del threshold | `protocol_numeric` con `calibration_id=NULL` evita la comprobación condicionada a `validation_calibration` |
| Segunda selected incompatible | Cambiar `source_record_key` evita la unicidad actual; no existe unicidad por evento/rol ni por identidad contractual |
| Hecho nuevo E10 etiquetado como legacy | Se pueden retirar los campos del evento y entrar por `source_kind='legacy'`; runtime tiene INSERT y no existe una admisión histórica exclusiva |
| Un miembro con model_version NULL y otro con modelo conocido | No se exige igualdad de ese linaje entre miembros cuando ya existe en uno |
| default huérfano | La guarda de pareja sólo se dispara al insertar/actualizar `run_threshold_calibration` |
| selected huérfano | Mismo problema; con `protocol_numeric` no se exige `calibration_id` |

Los rechazos de TEST para ambos roles, rol E10 no autorizado, checkpoint, dataset y población distintos, evento inexistente/NULL, duplicación de la clave original y NULL en campos obligatorios sí se observaron. SQLSTATE y marcador se verifican para esos once rechazos. No se confunde rechazo de una clave duplicada con unicidad contractual.

## Decisión E-04 propuesta, pendiente de aprobación

Autorizar el siguiente endurecimiento en v2, adicional a la ampliación de roles E-03:

1. **Pareja total y coherente.** Ampliar la validación diferida, también desde `evaluations`, para exigir exactamente ambos miembros y su registro de calibración al commit. Comparar checkpoint, training/run lineage, modelo cuando aplique, dataset, población, protocolo y contrato de entrada con igualdad que no deje escapar NULL. Para E10, exigir evento de calibración acreditado y coherencia del contenido con la proyección. Sin inventar procedencia ausente ni recalcular eventos históricos.
2. **Procedencia de threshold obligatoria por rol.** Para selected E10, exigir `threshold_source='validation_calibration'`, `calibration_id` no nulo, referencia inversa al propio miembro y threshold coincidente con la calibración VALIDATION. Default debe coincidir con el threshold contractual y no fingir una selección. Mantener las reglas actuales de TEST, E-01 y E-02.
3. **Unicidad persistente.** Imponer unicidad `(source_event_id, evaluation_role)` para miembros E10, más unicidad por identidad contractual de calibración —run/training lineage, modelo/checkpoint, dataset, población, protocolo, contrato de entrada y rol— con tratamiento explícito de NULL. La identidad no incluirá el threshold seleccionado: cambiarlo no debe permitir una segunda selected incompatible. El proyector tendrá claves deterministas con rol y un único límite transaccional que incluya ledger, registro de calibración, ambos miembros y métricas. ACCEPTED sólo después del commit; probar fallo en cada miembro y reintento.
4. **Admisión legacy exclusiva de adopción en v2.** Impedir que el login runtime cree evaluaciones nuevas `source_kind='legacy'`; reservar la carga histórica al recorrido de adopción controlado por migrador y evidencia archivada. No borrar ni reclasificar hechos existentes. PostgreSQL legacy conserva su escritor anterior. Esta política cambia quién puede insertar esos hechos en v2; no se debe resolver mediante un indicador JSON o GUC que el runtime pueda autodeclarar.
5. **Nueva recertificación integral.** Actualizar productor/proyector, validadores de adopción, generador, manifiesto, comparador, hashes y tests de forma coherente; ejecutar todo el apartado 7 en un nuevo destino aislado. Promover pins y expedir certificado sólo tras pasar los rechazos requeridos, atomicidad, D-01 a D-06 y ACL E-01. Después repetir E-02 y continuar la matriz E, empezando por el productor real de contexto.

Es una propuesta contractual concreta; esas guardas adicionales **no están implementadas ni aprobadas**. En particular, no se eligió silenciosamente restringir el ingreso legacy ni se alteró su comportamiento para hacer pasar las pruebas.

## Pendientes y alcance de la detención

No se emitió certificado E-03. No se ejecutaron todavía recertificación conductual D-01 a D-06, pruebas ACL E-01 por login, rollback de instalación con fallo, idempotencia, backup/restore ni regresión E-02 posterior a recertificación. La igualdad de sus objetos de catálogo con E.1 no sustituye esas pruebas. El rollback de fixtures de este diagnóstico tampoco sustituye rollback de instalación o atomicidad de ResultService.

Quedan pendientes el proyector de pareja, la producción real de `execution_parameters.e10_v2_evaluation_context_v1` y todos los recorridos integrales que estaban pendientes. La [matriz E](e10_10_5e_integration_results.md) no avanza por haber pasado un control SQL sintético. D.4 y E.1 son certificados históricos. No se declara «INTEGRACIÓN COMPLETADA» ni se solicita Gate E.

Sin acceso al PostgreSQL operativo, campañas reales, cutover, uso de TEST para calibración/selección ni cambios al dataset/splits.

## Reproducción del diagnóstico

Los scripts no leen configuración operativa. Las credenciales permanecen en rutas privadas referenciadas en `private_paths.json`, sin secretos en evidencia. El clúster de esta ejecución se detuvo conservando su volumen; para repetir, arrancar exclusivamente el container_id del descriptor y verificar su aislamiento. No volver a ejecutar `setup` sobre el directorio existente.

```sh
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python scripts/db/build_v2_baseline.py --check
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python -m pytest -q tests/db_v2
malaria_dl_local_project/.venv/bin/python scripts/db/probe_v2_e3_contract.py
malaria_dl_local_project/.venv/bin/python scripts/db/capture_v2_e3_diagnostic.py
```

El probe devuelve 1 mientras falten los rechazos; capture registra `certified=false` y nunca crea `certificate.json`. [Scripts de preparación](../../scripts/db/recertify_v2_e3.py), [probe](../../scripts/db/probe_v2_e3_contract.py) y [captura](../../scripts/db/capture_v2_e3_diagnostic.py).
