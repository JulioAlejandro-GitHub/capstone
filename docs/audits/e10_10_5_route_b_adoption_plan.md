# E10.10.5C — Plan de adopción Ruta B

**E10.10.5C — ADAPTADOR IMPLEMENTADO. PENDIENTE DE REVISIÓN Y APROBACIÓN PARA ENSAYO SOBRE COPIA AISLADA.**

Gate B aprobado por decisión expresa del usuario. Alcance autorizado: implementación y validación estática de C. No se ejecutó adopción, Docker, SQL contra PostgreSQL, backup de la base actual ni cutover.

## 1. Objetivo y alcance

Adaptador independiente de la instalación vacía `pg_v2_baseline`. Parte de la forma legacy auditada con head `20260922_01`; cualquier diferencia en una copia futura bloquea. No presume que la captura E10.10.1 describe la base actual. La implementación conserva las decisiones E10.10.4 y la certificación B; [entradas leídas y hashes](e10_10_5c_evidence/inputs.json).

## 2. Implementación entregada

[Paquete y contrato de uso](../../adoption_v2/README.md), `core.py`, `preflight.py`, `transforms.py`, `planner.py`, `ddl.py`, `execute.py`, CLI y contrato legacy congelado. [Inventario de archivos C](e10_10_5c_evidence/implementation_files.json). No se modificaron recursos ni manifiesto de baseline.

El inventario comprende 97 tablas legacy: 17 PROTECTED, 67 KEEP, 11 REFACTOR y 2 MERGE. El destino contiene 103 tablas incluyendo Alembic: se retienen 95, se añaden 8 y las dos MERGE se reemplazan por las vistas aprobadas. [Mapping de 105 objetos](e10_10_5_legacy_mapping.csv) y [cobertura por columna](e10_10_5c_evidence/column_mapping.json).

## 3. Identidad y condiciones previas

Descriptor exclusivo de D y Gate C aprobado; no se reutiliza B. Identifica UUID de aislamiento, contenedor completo, volumen, puerto local no operativo, base, OID y system identifier distinto del origen. Fija hashes de backup aislado, esquema, inventario y bindings. Se verifica Docker mediante las guardas de B, y PostgreSQL 17 mediante identidad nativa y privilegios de `capstone_v2_migrator` / `capstone_v2_runtime`.

La copia deberá prepararse en D con propiedad v2 y extensiones/secuencias conformes a Ruta A. C no provisiona ni restaura nada. No se reasignan usuarios de aplicación ni se copian privilegios administrativos del origen. [Preflight detallado](e10_10_5_adoption_preflight.md).

## 4. Preservación y mapeos científicos

De las 84 tablas clasificadas KEEP/PROTECTED, 83 conservan sus datos íntegramente; `alembic_version` tiene la transición explícita descrita en el punto 5. Se comprueban filas y hashes; credenciales, roles de aplicación, datasets congelados, pacientes/splits, versiones, fingerprints, tres modelos, campañas, intentos, eventos, ledgers y gobernanza no se regeneran. Las 11 REFACTOR conservan sus identificadores y los valores originales completos en el archivo privado, con comparación de la proyección prevista. Las dos MERGE conservan PK/payload en el archivo, hash y vínculo explícito a la medición. No se leen imágenes ni checkpoints para recalcular hashes; se conserva la evidencia registrada.

| Transformación | Regla implementada |
| --- | --- |
| run_configurations | Una configuración por TRAIN; canonical/hash originales contrastados contra la configuración congelada. Sin completar valores científicos faltantes. |
| evaluations | Fuente explícita y única, TRAIN/checkpoint/población/protocolo y contrato de comparación trazables; IDs deterministas sólo para entidades nuevas. |
| run_clinical_metrics | PK conservada, una medida por evaluación; counts enteros, tasas nullable calculadas conforme binary_nullable_v2 y contrastadas contra valores legacy. AUC original o NULL con motivo, nunca derivada de counts. |
| training_history | Preserva IDs; aliases loss/accuracy compatibles; ledger epoch y tabla unidos sólo cuando identidad y valores concuerdan. Payload epoch original intacto. |
| calibración | Exclusivamente VAL, default 0.5, target 0.98 y dos evaluaciones distintas enlazadas a misma población/TRAIN/checkpoint. Ningún umbral inventado. |
| matrices/reportes/EAV | Deben coincidir con una medición individual; conflictos de labels, counts, clase, support o ratios bloquean. Extensiones EAV exigen namespace explícito. |
| E10 | Bytes canonical_event, secuencias, identidad y hashes del ledger preservados; proyección evaluation_completed y epochs contrastada con payload fuente. |
| XAI | Padre único, input/modelo/checkpoint/procedencia y metadatos de artefactos contrastados. Padres incompletos permanecen intactos con disposición expresa; no se generan explicaciones, interpretaciones o revisiones. |
| external | Complementario, nunca VAL/TEST oficial; seis campos de origen/manifiestos y dataset_version_sources obligatorios. |
| publicación | Se comprueba FK compuesta modelo/TRAIN/checkpoint; la elegibilidad completa de servicios sigue fuera de C. |

La eliminación de `runs.parameters.training_results` exige haber proyectado su validación y conserva el payload original en archivo. Las relaciones secundarias no modificadas permanecen intactas. Una evidencia ambigua produce `Blocked(código, ubicación estructural)`; no incluye datos sensibles en el mensaje.

## 5. Transacción y recuperación previstas

Preflight de identidad antes de escribir; locks exclusivos de tablas; rechazo de sesiones adicionales y estados activos; inventario nuevo y bindings revisados. Archivo privado durable, fuera del repositorio y modo 0600, dentro de directorio propio 0700. Un único transaction context para delta, DML, validación, catálogo y revisión; READ COMMITTED con locks evita leer un snapshot anterior a su adquisición.

El delta contiene 617 sentencias: 66 preparación, 218 finalización, 21 probes de invariantes, 18 triggers nuevos y 294 ACL/propiedad de secuencia. Las 77 guardas legacy permanecen activas. Los probes temporales validan filas adoptadas; sólo esos probes se retiran, antes de instalar las nuevas guardas definitivas. No se deshabilitan triggers, no se eliminan restricciones para aceptar datos y no se usa `IF NOT EXISTS` para ocultar diferencias. DROP de las dos tablas MERGE pertenece al diseño aprobado y está condicionado al archivo/mapeo verificado dentro de la transacción.

Sólo tras comparación completa con el catálogo nativo de Ruta A se actualiza condicionalmente `alembic_version` de `20260922_01` a `pg_v2_baseline`, exigiendo una fila. No es `stamp` ni se usa para corregir estructuras. Head anterior y 22 entradas históricas quedan archivados. Error precommit: rollback de DDL/DML/head; archivos privados sobreviven. Commit incierto: no inferir éxito del recibo preparado; comprobar revisión/catálogo/reconciliación antes de continuar. Repetición con plan original fijado por hash: no-op si y sólo si todo coincide.

## 6. Validaciones realizadas

50 tests de C, 20 de baseline y 5 del sobre Alembic: **75 aprobados**, ocho comandos offline correctos. Parser, generación determinista, tipado/orden físico de columnas, cobertura, checksums de 22 SQL y 54 archivos históricos intactos. [Comandos reproducibles](e10_10_5c_evidence/commands.json), [resultados](e10_10_5c_evidence/static_results.json), [pruebas detalladas](e10_10_5_adoption_tests.md).

Las pruebas transaccionales de C utilizan drivers/Docker/conexiones simulados. Ninguna de ellas equivale a ejecutar el delta en PostgreSQL. La baseline sí conserva su certificado B en PostgreSQL 17.9.

## 7. Resultados y pruebas pendientes

Planificación determinista, preservación sintética, bloqueos, reconciliación simulada y secuencia de promoción aprobados. Pendientes de D: copia real aislada, identidad completa, inventario reciente, bindings científicos con evidencia suficiente, aplicación del delta en 17.9, catálogo instalado idéntico, rollback real, ausencia de head falso, repetición, backup/restore y recuperación frente a pérdida de conexión. No se declara que los datos actuales sean adoptables.

## 8. Riesgos y límites

[Registro de riesgos](e10_10_5_open_risks.md). Parser 18.4 no acredita ejecución del delta en 17.9. Los fixtures prueban proyecciones y rechazos, no todas las FK del servidor ni disponibilidades de artefactos. La comparación de catálogo usa el certificado B sin normalizar para esconder diferencias. Evidencia incompleta y nuevas incompatibilidades bloquean; un conflicto arquitectónico nuevo requiere decisión, no relajación de restricciones.

## 9. Cierre y Gate C

PostgreSQL operativo permanece intacto por esta etapa: ninguna conexión SQL ni acción Docker, ninguna modificación de datasets, modelos, usuarios, campañas, eventos o artefactos reales. No se inició D ni E y no se ejecutó cutover.

**Se solicita revisión y aprobación explícita de Gate C para ensayar exclusivamente sobre una copia aislada en E10.10.5D.**
