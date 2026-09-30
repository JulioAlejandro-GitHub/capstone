# Compatibilidad INSERT ... SELECT

PASS. Matriz dbv2_3_insert_select_matrix.csv: **177 columnas**, 16 tablas. Se compararon las definiciones reales de ambos PostgreSQL, no sólo nombres o conteos.

| Dominio | Inspeccionadas | Directas | Manejo técnico | Transformaciones semánticas | Bloqueadas |
|---|---:|---:|---:|---:|---:|
| DATASET | 13 | 12 | 1 | 0 | 0 |
| USUARIO | 3 | 3 | 0 | 0 | 0 |

Coinciden nombres/conjunto de columnas, tipos con precisión/escala, nulabilidad, collation, identity/generated, PK, UNIQUE, CHECK, índices, triggers y cuerpos/atributos de sus funciones. Las FK coinciden salvo ON DELETE de dataset_splits.dataset_id (CASCADE→RESTRICT) y dataset_split_images.dataset_id (SET NULL→RESTRICT), decisiones DBV2.1 que no afectan INSERT con padres presentes.

Doce defaults UUID cambian gen_random_uuid() por pg_catalog.gen_random_uuid(); no se evalúan porque los IDs se copian explícitamente. No hay identity ni generated columns entre las 177 columnas. No se transforma ningún ID o dato para conciliar esos defaults.

La tabla dataset_versions requiere manejo técnico: insertar status VALIDATED sólo cuando el origen sea FROZEN, cargar sources/assignments y restituir FROZEN antes de COMMIT. Es el procedimiento aprobado en dbv2_1_data_transfer.md; preserva frozen_at original no nulo. Los demás campos no cambian. Conservar FROZEN desde el primer INSERT impediría insertar hijos por triggers BEFORE: no se presenta falsamente como copia directa completa. Prueba real sintética con rollback: lifecycle_fixture_results.json.

El plan usa 16 INSERT SELECT con columnas explícitas. Las dos bases están en clusters diferentes; no existe SELECT nativo entre bases PostgreSQL. DBV2.4 deberá transportar las filas autorizadas desde un snapshot READ ONLY a tablas temporales de la sesión destino mediante COPY FROM STDIN, sin transformarlas; luego aplicará los INSERT SELECT del plan. Es transporte técnico acotado, no ETL semántico ni un nuevo framework. Las tablas temporales se eliminan automáticamente al cerrar la transacción y no cambian la baseline.

El plan contiene un punto explícito de carga de staging, validaciones de cantidades y vacío del destino, locks, restauración de estado y comparación bidireccional completa por EXCEPT ALL. No puede transferir datos reales si staging no fue poblado. No está preparado para ejecutar ciegamente en DBV2.3. Sintaxis/PLpgSQL, alcance y columnas validados offline: transfer_plan_static_validation.json. Archivo NO ejecutado.

Los datos científicos y las credenciales se conservan byte/valor a valor al final. audit_events no requiere transferencia y no hay padres fuera del conjunto autorizado. Detalle exhaustivo: compatibility_details.json.
