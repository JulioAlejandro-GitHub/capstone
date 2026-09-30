# Persistencia ante reinicio

PASS. Secuencia: verificar identidad/separación → capturar catálogo/filas → docker stop `1dc48428c6b938da6525754cc4f26d535814f1f8c101928487f7c0d630ce4971` → comprobar existencia y etiqueta persistent del volumen → docker start mismo ID → pg_isready → reconectar a mismo cluster/base/OID → comparar catálogo y datos.

Antes/después: head pg_v2_baseline; SHA-256 `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb`; sólo una fila en alembic_version y una en experiment_execution_gate. Cero fixtures/legacy/historia experimental. Volumen `capstone_v2_isolated_persistent_data` conservado; servicio activo.

Evidencia: state_before_restart.json, state_after_restart.json, restart_result.json, destination_identity.json, persistent_storage_inspection.json y destination_commands.jsonl. No hubo operación de eliminación ni recreación de almacenamiento.

**BD-V2 PERSISTE PARA DBV2.4**.
