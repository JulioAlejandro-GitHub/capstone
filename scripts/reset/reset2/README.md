# RESET.2 — preparación detenida

Estado: **STOP_INVENTORY_DRIFT**. No hay ejecutor de reset aprobado.

- `operational.py` es únicamente una barrera ejecutable: siempre termina con código 2, antes de abrir conexiones o mover archivos. No acepta desbloqueo por flags ni variables.
- `precheck.py` consulta la identidad canónica, estados, GlobalGate, actividad, locks y fingerprints mediante una transacción READ ONLY. Requiere `manifest.json` (copia exacta del manifiesto RESET.1 aprobado) junto al script y el módulo `common.py` de RESET.1B en PYTHONPATH, además del entorno Python del backend. No reserva intentos. Un inventario distinto devuelve JSON de divergencias y exit 2. Un exit 0 sólo acredita este subconjunto de comprobaciones SQL, nunca autoriza el reset ni acredita congelación, archivos o backup.
- `reset1b_execution.diff` contiene el diff completo entre las copias retenidas del ensayo y los dos ejecutables finales revisados.
- `reset1b_worktree.diff` contiene el diff de HEAD y los archivos RESET.1B sin seguimiento, incluidos sus documentos. Los hashes se registran en la evidencia RESET.2.

Los archivos RESET.1B permanecen intactos. No se reejecutó su runner: incluye una migración, prohibida en esta etapa. La repetición afectada debe usar un procedimiento independiente, sin migración, una vez resuelta la divergencia y validado un backup nuevo.

Consultar `docs/engineering/e10_execution_refactor/reset_2_operational_preparation.md` para el bloqueo, evidencia y trabajo pendiente. No utilizar estos artefactos como autorización de mantenimiento operativo.
