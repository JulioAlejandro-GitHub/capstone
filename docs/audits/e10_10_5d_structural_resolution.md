# E10.10.5D.1 — Resolución estructural: diagnóstico y decisión pendiente

**E10.10.5D — BLOQUEADA. GATE D NO APROBABLE.**

## 1. Alcance y condición de parada
D.1 autorizada para corrección controlada exclusivamente sobre backups y entornos PostgreSQL 17.9 aislados. Se investigaron ambos bloqueos y se demostró una diferencia real de comportamiento en D-02. Se aplica la instrucción expresa de la Parte 2: «Si no son equivalentes, detenerse y presentar una decisión específica antes de cambiar el esquema». Por ello no se modificaron baseline, manifiesto, comparador ni adaptador; D-01 queda con corrección mínima propuesta y comprobable. No se reclama resolución completa ni nueva certificación.

## 2. Entornos e identidad
Se reanudó exclusivamente el contenedor D `09aeb81b36210177134e73c1d735967f2d053e6d4fb8723e3783a14a43787cc3`, clúster `7691066755790737451`, PostgreSQL `170009`, puerto loopback 55479 y volumen independiente conservado. Se verificaron las guardas Docker y la identidad SQL.
Se crearon dos bases auxiliares vacías, con OID registrado antes de DDL/datos: sufijos `_d1_legacy` y `_d1_baseline`. La primera restauró el backup fuente conservado, con hash comprobado; la segunda representó los recursos de la baseline anterior en PostgreSQL. Esta representación es diagnóstica: no ejecutó Alembic, no insertó head y **no constituye una instalación certificada de Ruta A**. [Identidades](e10_10_5d1_evidence/auxiliary_identities.json).

## 3. D-01 — definición y comportamiento
[Catálogo completo](e10_10_5d1_evidence/auxiliary_catalogs.json), [lectura inicial](e10_10_5d1_evidence/diagnostic.json), [ownership/ACL](e10_10_5d1_evidence/ownership_privileges.json).

| Propiedad | Legacy restaurado | Baseline previa |
| --- | --- | --- |
| Columna | bigint NOT NULL GENERATED ALWAYS AS IDENTITY | bigint NOT NULL |
| pg_attribute.attidentity | a (ALWAYS) | vacío |
| pg_attrdef de id | ausente | ausente |
| pg_depend de secuencia | i, dependencia interna de columna | a, dependencia automática |
| pg_sequence | bigint, start/increment/min/cache 1, max 9223372036854775807, cycle false | mismos parámetros |
| Propietario tabla/secuencia | capstone_v2_migrator | capstone_v2_migrator |
| Valor inicial | last_value=1, is_called=false | igual |
| INSERT omitiendo id | genera id=1 | rechaza 23502 (NOT NULL) |
| INSERT id explícito | rechaza 428C9 | acepta |
| OVERRIDING SYSTEM VALUE | acepta id explícito | acepta id explícito |

La `a` de attidentity significa ALWAYS y no debe confundirse con la `a` de pg_depend (dependencia automática). La baseline perdió la semántica de generación y la protección frente a IDs explícitos. No es una diferencia cosmética.
Los INSERT ocurrieron exclusivamente en bases auxiliares y sus filas se revirtieron. La secuencia IDENTITY auxiliar quedó `is_called=true`, porque nextval no se revierte; se registró, no se ocultó ni se restauró con setval. La copia D original conservó `1,false`.
Los ACL distintos de la auxiliar restaurada (`--no-acl`) y la baseline reflejan preparación declarada: runtime no tiene INSERT/USAGE en la primera y sí en la segunda. No se presentan como ACL operativos ni se normalizan. Las pruebas básicas de INSERT se hicieron como administrador aislado para separar IDENTITY de privilegios.

**Propuesta mínima D-01, no aplicada:** en el generador de baseline, conservar `id bigint GENERATED ALWAYS AS IDENTITY NOT NULL`; retirar el CREATE SEQUENCE independiente y el ALTER SEQUENCE OWNED BY de esa columna, pues PostgreSQL creará su secuencia interna con el mismo nombre. Conservar parámetros, ACL contractuales y ownership. Representar identity explícitamente en metadatos del manifiesto, comprobación estática y comparador de columnas. No cambiar pg_catalog ni convertir legacy a DEFAULT nextval(). No ejecutar ALTER de identity sobre la copia legacy. Reconstruir Ruta A en base vacía y repetir catálogo, restricciones, E10, rollback, idempotencia y restore antes de cambiar el hash certificado consumido por adopción.

## 4. D-02 — inventario exacto y resolución real
[Inventario por tabla/columna](e10_10_5d1_evidence/default_inventory.json): **41** defaults legacy afectados por representación; **39** columnas retenidas resuelven a otra función en la baseline. Los otros dos pertenecen a `classification_reports` y `confusion_matrices`, reemplazadas por vistas según MERGE aprobado, sin default de columna física destino.
Se registran expresión legacy bajo ambos search_path, expresión v2, tipo uuid, árbol nativo pg_attrdef.adbin, función resuelta, dependencias y propuesta por columna. Los OID son evidencia local del clúster, no claves para comparar entre clústeres.

- Legacy resuelve `pg_catalog.gen_random_uuid()` (funcid 3432 en este clúster), lenguaje internal, símbolo gen_random_uuid, tipo uuid. Bajo `public,pg_catalog` PostgreSQL imprime el nombre cualificado; bajo `pg_catalog,public` imprime gen_random_uuid(). El árbol almacenado permanece idéntico: esa parte sí es representación.
- La baseline, creada con `public,pg_catalog` tras CREATE EXTENSION pgcrypto, resuelve `public.gen_random_uuid()` de pgcrypto, lenguaje C, símbolo pg_random_uuid, librería $libdir/pgcrypto. El default posee dependencia normal de esa función; el default legacy no posee esa dependencia de extensión. Objetos internos fijados por PostgreSQL pueden omitir dependencias explícitas de pg_depend; el árbol adbin prueba el binding.
- Ambas generan UUID aleatorio mediante el núcleo; la documentación oficial describe la función de pgcrypto como wrapper obsoleto de la función del núcleo. Eso **no implica equivalencia de dependencias o permisos**. Fuente: https://www.postgresql.org/docs/17/pgcrypto.html#PGCRYPTO-RANDOM-DATA-FUNCS.

**Prueba discriminante en PostgreSQL 17.9:** tabla auxiliar con el default realmente resuelto, permisos de tabla iguales para runtime, y REVOKE EXECUTE sobre public.gen_random_uuid() dentro de una transacción auxiliar. Legacy inserta correctamente; baseline falla con SQLSTATE **42501**. El REVOKE y la tabla de prueba se revierten; nunca se ejecutan en la copia D original ni en operativo. [Resultados](e10_10_5d1_evidence/behavior_tests.json).
No se normalizan los dos bindings como si fueran el mismo objeto. No basta retirar prefijos del comparador ni elegir un search_path que imprima nombres parecidos.

## 5. Decisión específica solicitada
**Aprobar que la baseline v2 conserve el binding legacy de las 39 columnas retenidas mediante `DEFAULT pg_catalog.gen_random_uuid()`, junto con la conservación de `GENERATED ALWAYS AS IDENTITY` de D-01.** Esto elimina la dependencia accidental de los defaults retenidos respecto del wrapper de pgcrypto. No retira pgcrypto ni cambia datos/UUID existentes ni la función núcleo. Las dos tablas MERGE mantienen su mapping aprobado. Los defaults de entidades nuevas requieren inventario separado; no se amplía esta decisión a columnas nuevas por sustitución global de texto.
Tras aprobar: aplicar correcciones mínimas, actualizar manifiesto y metadatos, certificar una nueva Ruta A y fijar su hash; corregir la comparación de representación solo para el mismo objeto resuelto, respaldada por pg_get_expr/árbol y dependencias en PostgreSQL 17.9. Repetir preflight D completo y continuar únicamente si todas las guardas pasan. La autorización actual para corregir D-01 no elimina la parada explícita de D-02 ante una diferencia real.

## 6. Preservación
[Comparación posterior](e10_10_5d1_evidence/preservation.json): **97/97 tablas de la copia D original conservan conteos y hashes canónicos completos** respecto de D; secuencia original `last_value=1,is_called=false`. Incluye usuarios, dataset/asignaciones, modelos, campañas/gate, eventos y ledger histórico. No se leyeron ni modificaron archivos científicos. Cero conexiones operativas durante D.1.
Backups intactos: source.dump SHA-256 `fa50d1dedb10e2a04aa99125143f2b74c213eceb679db1e69ffc1d9a882b71f6`; isolated.dump SHA-256 `c197888c05358e2c28e8b5c80c7a7ec01751b8548eb9b2c56918d5af3cd6e281`. Conservados privadamente fuera del repositorio. Esta preservación D→D.1 no sustituye la equivalencia origen→adoptado aún pendiente.

## 7. Código y comandos
Añadidos únicamente scripts diagnósticos: `scripts/db/diagnose_v2_structure.py`, `scripts/db/probe_v2_structural_behavior.py` y `scripts/db/probe_v2_structural_privileges.py`. Ningún cambio de código productivo, baseline o comparador. Los scripts fijan el descriptor D, validan identidad y nunca usan la configuración operativa. El runner de probes crea nombres nuevos de auxiliares y falla si ya existen; no reejecutar a ciegas sobre los nombres conservados.

Comandos efectivos, todos salida 0:
```
docker --host unix:///Users/julio/.docker/run/docker.sock start 09aeb81b36210177134e73c1d735967f2d053e6d4fb8723e3783a14a43787cc3
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python scripts/db/diagnose_v2_structure.py
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python scripts/db/probe_v2_structural_behavior.py
PYTHONPATH=/private/tmp/e10_10_5d_parser312:. malaria_dl_local_project/.venv/bin/python /private/tmp/d1_extra.py
docker --host unix:///Users/julio/.docker/run/docker.sock stop 09aeb81b36210177134e73c1d735967f2d053e6d4fb8723e3783a14a43787cc3
```
`d1_extra.py` está conservado idéntico como `probe_v2_structural_privileges.py`. Consultas exactas en diagnostic.json y ownership_privileges.json; pg_restore y código de salida en aux_restore.json. No se publican contraseñas ni filas científicas. Hashes de código y evidencia en artifact_hashes.json.

## 8. Certificación anterior y pruebas pendientes
Ruta A certificada en B corresponde exclusivamente al manifiesto `c1063136941e9429373d91d666fbea5d25afd0dc39f111fdf2b9779aa1f51eb0` y catálogo `df07e6bfc58c21f8290ffb63324a8f3e57b4561e4fe12be74ce576be993fc58b`. Es **anterior a la revisión propuesta D.1**. Sus pruebas no acreditan las correcciones propuestas. Ambos hashes siguen intactos; no existe baseline modificada ni recertificada en esta entrega.
No se ejecutaron adopción, preflight completo aprobado, rollback de adopción, repetición ni backup/restore adoptado. No se declara preservado el comportamiento E10 de una baseline corregida hasta ejecutar sus pruebas. Los probes demuestran el defecto anterior, no una corrección instalada.

## 9. Cierre
**E10.10.5D — BLOQUEADA. GATE D NO APROBABLE.** Se solicita únicamente la decisión específica de defaults del punto 5, no Gate D. Contenedor aislado detenido, volumen y auxiliares conservados. No E, cutover, modificación del origen ni reparación científica.
