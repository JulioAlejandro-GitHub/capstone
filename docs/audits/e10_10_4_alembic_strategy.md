# E10.10.4 — Nueva baseline Alembic, bootstrap y adopción
> Actualización E10.10.5A: A-01 fue aprobada por el usuario. La sección final documenta la enmienda; el cuerpo original conserva su contexto histórico. Implementación y límites actuales: [e10_10_5_implementation.md](e10_10_5_implementation.md).

**Diseño; no revisión implementada, SQL ejecutado ni stamp.** La baseline representa v2, incluidas las consolidaciones, normalización, XAI y FK de publicación; no es otra revisión vacía sobre SQL histórico.

## 1. Estado acreditado y destino

Hoy `alembic.ini` usa `alembic/` raíz. La revisión inicial `20260726_00_legacy_029_baseline.py` no crea tablas; necesita fundación SQL histórica. El entorno vigente capturado tiene head `20260922_01`, 22 registros de schema_migrations y 23 archivos SQL numerados presentes; `004_seed.sql` no fue aplicado. Los 22 checksums coinciden en auditoría previa. No existen dos migradores operativos autónomos por dominio: Alembic ya modifica ML, clínica, campañas y E10.

DP: nueva línea independiente con revisión raíz nominal `pg_v2_baseline` (ID final a aprobar), `down_revision=None`, ubicación distinta durante desarrollo, p.ej. `alembic_v2/`. Evitar incluir simultáneamente dos raíces como heads de un mismo entorno canónico. Después del corte, sólo el entorno v2 participa en `upgrade head`; las revisiones antiguas y los 22 SQL quedan archivados **sin modificar bytes ni renumerarlos**, con manifiesto SHA-256 y documentación de procedencia. Se conserva también el seed excluido como evidencia de exclusión; no se instala.

No copiar sólo Base.metadata ni ejecutar 22 SQL desde una revisión. La futura revisión debe contener la construcción integral de v2, usando definiciones SQL explícitas versionadas donde corresponda. El DDL conceptual de esta entrega incluye las tablas conservadas, objetos procedimentales, vistas e índices más cambios v2; su organización por catálogo+alteraciones expresa el estado final, no un upgrade operativo ni una baseline ya probada.

## 2. Orden de objetos de una instalación vacía

| Fase | Objetos | Tratamiento |
| --- | --- | --- |
| 0 | Identidad de target, rol migrador, bloqueo exclusivo de migración | Preflight impide confundir instancia operativa con fixture. Una conexión canónica, search_path explícito. |
| 1 | public, plpgsql incorporado, pgcrypto | CREATE EXTENSION revisado; no introducir otras extensiones por comodidad. |
| 2 | Secuencia propia de experiment_execution_events | Definir y asociar OWNED BY después de tabla/columna. No copiar last_value de otra instalación. |
| 3 | Tablas/columnas/tipos/defaults/NOT NULL | Orden sin FK para resolver ciclos: 95 conservadas y 8 nuevas. alembic_version la administra Alembic; no crearla dos veces. |
| 4 | Funciones usadas por CHECK y guards | Cuerpos SQL/PLpgSQL explícitos, firmas/sobrecargas y search_path completo; ninguna función de extensión copiada manualmente. |
| 5 | PK y UNIQUE | Antes de FK, incluyendo claves compuestas existentes y nuevas. |
| 6 | CHECK y FK | FK diferibles de campaña/controlled preservadas; no convertir NO ACTION diferible a RESTRICT indiscriminadamente. |
| 7 | Índices independientes | No duplicar índices creados por PK/UNIQUE; preservar predicados de exclusión y E10. El índice no único de history(run,phase,epoch) se sustituye por uq_v2_epoch. |
| 8 | Vistas | Orden topológico: base → agregados; incluir vistas de compatibilidad y v2. No emitir SELECT * si cambia shape. |
| 9 | Triggers | Sólo 77 triggers de aplicación conservados más v2; no crear manualmente triggers internos RI. Constraint triggers diferidos se emiten como triggers, no como ADD CONSTRAINT genérico. |
| 10 | Ownership, ACL y permisos de aplicación | Roles administrativos explícitos y privilegios mínimos; no alterar usuarios/roles de aplicación protegidos. |
| 11 | Estado técnico mínimo y verificación | Singleton libre del gate según definición vigente; cero usuarios/datasets/modelos científicos sembrados; versión gestionada por Alembic. |

El archivo conceptual reproduce 65 funciones propias y sus variantes, no las 36 de pgcrypto. `SET check_function_bodies=false` permite declarar cuerpos con referencias hacia adelante; no es sustituto de validación. La implementación debe reactivar verificación, resolver dependencias y probar invocación de guards con fixtures aisladas. Cada función se inventaría con nombre+argumentos, cuerpo, volatility, security y search_path; cada trigger con timing/eventos/predicado/deferrability.

Autogenerate sirve para detectar drift básico, no como autor de baseline. Revisar especialmente SQL de funciones, triggers, vistas, índices parciales/expresiones, defaults y CHECK. La documentación oficial advierte que las migraciones generadas requieren revisión y no detectan todas las construcciones. [Alembic: autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).

## 3. Ruta A — Instalación vacía

1. En fase futura aprobada, crear un target **aislado** sin datos científicos. El instalador verifica DB/schema esperado y ausencia de tablas de aplicación. Si encuentra esquema legacy, aborta y remite a Ruta B; no usa IF NOT EXISTS para ocultar una instalación parcial.
2. Configurar sólo el directorio de revisiones v2. `upgrade head` futuro crea todo lo listado, sin bootstrap histórico ni dependencia de 001–029. El seed de autenticación/dataset no es parte del esquema.
3. Registrar automáticamente revisión v2 al completar la transacción. Insertar únicamente el estado técnico indispensable del gate libre en una operación explícita de bootstrap gobernada; no copiar owner, PID ni jobs de otro entorno.
4. Comparar catálogo contra manifiesto objetivo: tablas, columnas/types/typmods/defaults/nullable, PK/FK/UNIQUE/CHECK/validated, índices claves/opclasses/predicados/readiness, funciones/cuerpos/search_path, triggers habilitados y vistas/dependencias.
5. Ejecutar pruebas sintéticas de E10, publicación, métricas y XAI en target aislado. Ninguna prueba necesita TRAIN, TensorFlow ni imágenes oficiales. Fixtures mínimas de schema/domain con valores sintéticos.
6. Probar backup/restore de esa instalación, repeatability del bootstrap y fallo atómico si una fase no completa. Una segunda invocación de upgrade es no-op; no recrea seed ni genera historial.

**Criterio:** instalación vacía operable estructuralmente por Alembic, no una plataforma con dataset o credenciales productivas precargadas. Importar datos científicos es un proceso independiente expresamente autorizado.

## 4. Ruta B — Adopción del entorno existente

No es un `upgrade` directo de la raíz anterior a la nueva raíz. Es transformación controlada de una copia y certificación de equivalencia antes de registrar la nueva baseline. Evitar `stamp` sobre origen para que una etiqueta aparente resolver objetos faltantes.

1. Autorizar y preparar copia verificable con respaldo/restauración ensayados. Congelar escritores al momento del cutover, no durante toda la etapa de diseño. Las políticas de backup incluyen datos protegidos sin exportarlos en documentos.
2. Preflight en copia: identidad, revisión única 20260922_01, 22 checksums históricos contra archivos, objetos E10/cuerpos/search_path, gate libre y ausencia de jobs/sesiones activas. Estado activo detiene adopción: no liberar owners ni marcar intentos completed para facilitar migración.
3. Inventariar de nuevo filas experimentales: el baseline vacío es evidencia histórica, no garantía futura. Mapear cada origen mediante matriz. Preservar identidades, split, versiones, materializaciones, rutas y autenticación; no recalcular checksums físicos de imágenes ni reconstruir dataset.
4. Transformar **sólo copia** con un adaptador de adopción separado, revisable e idempotente. Crear destinos, materializar configuration/evaluations/métricas y manifiestos de origen; resolver aliases; preservar hashes originales. Datos ambiguos generan informe y abortan. No simular valores por ausencia ni usar TEST para completar calibración.
5. Consolidar matrices/reportes sólo después de verificar equivalencia, adaptar writers/readers y guardar evidencia de IDs/metadata originales. Crear vistas homónimas. No usar CASCADE indiscriminado para eliminar dependencias.
6. Verificar catálogo final contra Ruta A, exceptuando únicamente diferencias **de datos históricos** esperadas en ledgers. Comprobar todos los objetos validados y fingerprints científicos almacenados/recuentos SQL; no repetir hashing de imágenes. Preservación de contraseñas se comprueba sin mostrarlas.
7. Probar contratos backend/Local/Docker/reporters/campañas/React con mocks y datos sintéticos separados. Verificar semántica de éxito, pérdida de ACK, fencing, final locks TEST y publicación.
8. Sólo con equivalencia aprobada registrar revisión v2 **en copia** mediante operación explícita de adopción (futuro stamp autorizado), guardando revisión previa, checksums y manifiesto de equivalencia en evidencia de adopción. Hoy no se ejecuta stamp ni se borra ledger.
9. Cutover futuro con decisión separada: mantenimiento, respaldo final, aplicación compatible, promoción de copia y validaciones de lectura. No mantener dos bases científicas escritoras en paralelo. Conservar origen archivado sin conexiones de aplicación según procedimiento aprobado.

La equivalencia no significa que A y B contengan los mismos datos: significa esquema/contratos iguales y conservación de la ciencia existente en B. La instancia vacía A no recibe usuarios/versiones por defecto.

## 5. Ledgers y archivo histórico

| Objeto | Ruta A | Ruta B | Política futura |
| --- | --- | --- | --- |
| schema_migrations | Tabla vacía reservada a evidencia histórica; no simular 22 archivos aplicados | Preservar exactamente 22 filas/checksums actuales, o los realmente presentes y auditados en copia | Sin nuevo writer de esquema. No usarla como segundo head ni borrarla en E10.10.4. |
| alembic_version | Creada/controlada por entorno v2 | Registrar v2 sólo tras equivalencia; revisión anterior archivada fuera de esta tabla | Una fila y un head canónico. No dos revisiones independientes simultáneas. |
| SQL históricos | Archivo inmutable; sin ejecución de bootstrap | Igual, usados sólo para verificar evidencia y entender origen | 22 aplicados + seed excluido conservados; no editar checksums para aprobar preflight. |
| Revisiones anteriores | Archivo separado de búsqueda de heads | Evidencia exacta de historia previa | Sin reescritura ni downgrade automático. |

La tabla schema_migrations conservada no impone usar SQL antiguo. Su existencia conserva procedencia; el migrador v2 no la consulta como capacidad vigente. Si en el futuro se decide retirarla, requerirá exportación íntegra y aprobación distinta.

## 6. Guards E10 y preflight

EV: `execution/schema.py` requiere exactamente E10_REVISION='20260922_01', columnas sin typmod event_id/event_sequence, expresión CHECK exacta, dos UNIQUE parciales, trigger `a_train_event_guard`, MD5 de función y `search_path`. Un head nuevo rompe reservas aunque sea compatible. No se modificó ese archivo.

DP: contrato de capacidades versionado con allowlist explícita `{legacy:20260922_01, v2:pg_v2_baseline}` durante despliegue coordinado. Cada revisión exige **su conjunto** de capacidades, no OR genérico entre comprobaciones. V2 añade evaluaciones/configuración, integridad compuesta y trigger de proyección; desconocidos fallan antes de reservar. Conservar owner/fencing/índices E10 exactos y hash legacy. La nueva columna event_sequence sigue numeric sin typmod: no convertirla a integer por comodidad, pues el guard lo detecta.

Código compatible se despliega en ventana sin nuevas reservas o antes del corte si admite ambas versiones con proyección diferenciada explícita. No aceptar cualquier revisión mayor ni comparar strings lexicográficamente. No usar stamp como remedio de E10_SCHEMA_NOT_READY. `verify_alembic_adoption.py` se divide en preflight legado de Ruta B (22 checksums completos) y verificador v2 de capacidades; un entorno A no falla por no tener entradas SQL antiguas.

`Makefile`, `scripts/db/migrate.sh`, `validate_alembic_transactionally.py`, bootstrap_probe y herramientas de reset deben resolver el entorno adecuado sin invocar init_db histórico. Ningún guard debe ejecutar una migración. Instalación y verificación son acciones separadas, con conexiones/roles separados.

## 7. Transacciones, fallos y reversión

Baseline vacía: DDL transaccional ordinario; no CREATE INDEX CONCURRENTLY. El validador actual usa conexión/savepoint y promete rollback; no introducir autocommit que lo invalide. Si futuras tablas pobladas exigen índices concurrentes, se diseña otro runner/rehearsal con recuperación de índices inválidos, nunca se esconde ese cambio en la baseline.

El rollback operativo de adopción es conservar/promover origen y aplicación compatibles según ventana; no ejecutar un downgrade que borre ciencia v2. Antes de abrir writes v2 puede revertirse el cutover; después requiere reconciliación explícita de nuevas escrituras. No afirmar que el backup elimina pérdida potencial tras el corte. Corregir esquema por forward migration cuando sea más seguro.

## 8. Matriz de certificación futura

| Prueba | Resultado exigido |
| --- | --- |
| Empty → v2 | 103 tablas, vistas y cuerpos completos; cero dependencia ejecutiva de SQL históricos. |
| Copy legacy → v2 | Misma firma de catálogo A, datos protegidos invariantes y mappings completos. |
| Fallo DDL medio baseline | No head falso ni objetos parciales persistentes. |
| Hash histórico alterado/faltante | B aborta sin reserva/migración; A no depende del archivo. |
| Guard viejo/nuevo/desconocido | Sólo combinaciones revisadas admitidas; versiones desconocidas rechazadas. |
| Objeto omitido/trigger deshabilitado | Preflight detecta daño aun con alembic_version correcta. |
| E10 replay/carreras/rollback | Idempotencia global/secuencia y proyección atómica. |
| Métricas y publicación | NULL definido, conteos y FK exactos; misma regla TRAIN/EVALUATE. |
| Restore aislado | Funciones, constraints y triggers reproducidos, no sólo tablas. |

Este documento no contiene autorización ni instrucciones ejecutadas contra PostgreSQL operativo.

## Enmienda A-01 aprobada — 2026-09-29

**A-01 RESUELTA POR DECISIÓN ARQUITECTÓNICA — E10.10.5A PUEDE REANUDARSE.** Autorización explícita del usuario, limitada a diseño, baseline y validación estática; no autoriza B ni cutover. El texto anterior conserva la decisión original. Sus hashes y la definición original de evaluations están en [e10_10_5a_design_before_a01.json](e10_10_5a_design_before_a01.json); el bloqueo original se conserva en [e10_10_5a_initial_block.md](e10_10_5a_initial_block.md).

- `evaluations.split` admite `external` además de los tres splits oficiales. `external_validation` permanece intacto en el dataset protegido; no se crea un alias ni mapping automático.
- Ámbito (`split`), población (`population_hash` y manifiesto), origen (`dataset_origin_id`, `dataset_origin_role` y evidencia de procedencia), protocolo (`protocol_hash/version/snapshot`) y finalidad (`purpose`) son conceptos independientes.
- External exige `purpose=complementary`, `evaluation_role=external_complementary`, manifiestos de población/procedencia recuperables con SHA-256 y FK a la PK existente `(dataset_version_id,dataset_id,role)` del origen registrado en `dataset_version_sources`, sin añadir UNIQUE al dominio protegido. La versión evaluada puede diferir de la versión de entrenamiento; se conserva íntegro el linaje TRAIN/checkpoint/modelo. No se crean versiones ni fuentes ficticias para completar esa FK.
- `source_kind=external_record` identifica nuevas entradas externas; `legacy` permite adopción con evidencia suficiente. No se hace pasar una entrada externa por evento E10 ni por assessment cuyo contrato actual sólo admite splits oficiales.
- Se prohíbe usar external como calibración, selección de checkpoint/modelo, VALIDATION sustitutiva o agregado TEST oficial. Los roles y la finalidad lo impiden en evaluations, el par de calibración exige val, y `vw_v2_model_comparison` sólo contiene train/val/test. `vw_v2_external_evidence` expone evidencia complementaria sin agregación, con población, protocolo y procedencia. El catálogo pasa de 32 a **33 vistas**; mantiene **103 tablas**.
- `run_clinical_metrics.split_name` sigue representando `external`; su trigger lo deriva de la evaluación externa trazada. Se conservan el lector/escritor legacy en la aplicación operativa. Adaptar esos escritores al contrato transaccional v2 corresponde a E10.10.5E: esta enmienda no afirma compatibilidad binaria de INSERT antiguos que carezcan de evaluation_id.
- La existencia de un URI/hash no certifica disponibilidad o validez científica del manifiesto. La adopción abortará sin mapping si falta evidencia; los servicios deben verificar procedencia y políticas de selección. No se modifican imágenes, asignaciones ni hashes históricos.


## Resolución B-01 — roles de instalación v2 (2026-09-29)

Por decisión arquitectónica aprobada, el propietario/migrador se denomina `capstone_v2_migrator` y el runtime independiente `capstone_v2_runtime`. Ambos carecen de SUPERUSER, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS y memberships. El runtime no dispone de DDL, TEMP, TRUNCATE ni escritura en alembic_version o modificación directa de los ledgers protegidos. Sólo se provisionan en el destino aislado autorizado para B. La evidencia de los nombres reservados anteriores se conserva en el informe B-01.
