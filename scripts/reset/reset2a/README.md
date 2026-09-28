# RESET.2A: reconciliación y recuperación aislada

No hay vía operativa de DELETE. Se mantienen sin cambios todos los scripts y guards RESET.1B; RESET.2 sigue bloqueado para ejecución operativa.

## Procedimiento reproducible

1. Usar `python3 scripts/reset/reset1b/run.py prepare --work /private/tmp/<directorio-nuevo>` para crear un clon validado por etiqueta, base, schema, cluster, rol y volúmenes, restaurando el backup histórico de RESET.1. Esto no genera un backup nuevo. El runner rechaza reutilizar un target existente.
2. Copiar `reconcile.py` y `recovery.py` a `backend_work` del target privado. Ejecutarlos con Python del backend y PYTHONPATH que contenga ese directorio, `/app/malaria_dl_local_project` y `/app`. No imprimir el archivo privado `target.json`: contiene credenciales del clon.
3. `reconcile.py` compara las 97 tablas del golden restaurado con SELECT READ ONLY operativos; exige exactamente el evento autorizado y un único cambio `last_login_at`. Cualquier otra diferencia detiene el proceso. Sólo en el clon reproduce ambos cambios y comprueba igualdad exacta de las 97 tablas; genera `reconciled_baseline.json` sin sobrescribir `manifest.json`.
4. En el primer clon ejecutar `recovery.py --case success`: fallo SQL posterior a todos los DELETE y a cuarentena de copias; rollback y restauración verificados; repetición integral con commit confirmado.
5. En otro clon nuevo, repetir la reconciliación y ejecutar `recovery.py --case lost_ack`: commit PostgreSQL real seguido de una excepción inyectada en Python. Comprobar COMMIT_UNCERTAIN, ninguna restauración automática, conexión física nueva y todas las postcondiciones antes de confirmar el resultado e invalidar la caché desechable.
6. Usar `run.py finish` en cada directorio privado para comprobar invariancia operativa y de fuentes, retirar sólo las copias marcadas y eliminar sólo sus contenedores/volúmenes desechables.

**No ejecutar `run.py rehearse` en RESET.2A**: incluye una migración. Aquí se importa el módulo final sin invocar su `main`; se compila el nodo AST exacto que controla reset/cuarentena/commit/recuperación y se ejecuta con `reset()` real, SQL real y filesystem de copias real. El resto de comprobaciones posteriores se realiza en el driver nuevo. No se afirma haber ejecutado el `main` completo ni validado de nuevo su sección E10.

El proxy de COMMIT delega en la conexión/transacción real y sólo inyecta la excepción después del retorno del commit real. No es una caída de red, un proceso terminado ni una prueba de durabilidad ante pérdida de energía. La instrumentación de `restore()` registra las llamadas y delega en el movimiento real de copias; no sustituye el filesystem por un doble.

Los journals de RESET.1B son suficientes para este ensayo controlado en proceso; no acreditan durabilidad por fsync ni recuperación de una caída del host. La futura vía operativa debe completar sus propios controles de autorización, ventana sin escritores, backup nuevo, cuarentena persistente y reconciliación de estados no concluyentes.

La línea base v1 es un artefacto separado. `tables` y `reconciliation` definen sus hashes actuales y cambios autorizados; los apartados heredados del manifiesto (incluido el backup) documentan el golden histórico. No usar ese backup histórico como si fuese el nuevo backup operativo de RESET.2.
