# E5 — Evidencia de integración sintética

El usuario ejecutó desde Compose autorizado:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE5_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaign_executor_postgres.py -k 'not public_e5_revision_readonly'
```

Resultado aportado: **13 passed, 1 deselected in 3.76s**. Es evidencia de la terminal del usuario, no ejecución del asistente. Al recibirla, HEAD sigue siendo `cd5c64d703358797570f5183dd598d93314dc0eb` y los **16/16 hashes** del manifiesto E5 coinciden. Se preservaron todos los cambios existentes. La salida no incluye una captura independiente de hashes dentro del contenedor.

La ejecución acredita las aserciones sintéticas preparadas: matriz de doce y reanudación sin repetir, fallos individuales y presupuestos, idempotencia y propietario revocado, pausa sistémica, exit0 incompleto, competencia por un único miembro, interrupción controlada y seis puntos de fallo conservando evidencia. Incluye rollback/limpieza del fixture y comprobación posterior desde otra conexión. El caso concurrente utiliza commits únicamente en esquema sintético y lo elimina al finalizar.

No se convierte la prueba after_accept en evidencia de commit incierto real, ni KeyboardInterrupt en prueba de caída del host. No acredita entrenamiento científico, desempeño clínico ni durabilidad ante reinicio. Se mantienen los límites documentados del informe E5.

La única prueba deseleccionada comprueba la revisión y estructuras públicas. Instalación operativa y comprobación pública: **PENDIENTES**. El nuevo intento del asistente de `make db-migrate-check` falló por acceso denegado a Docker API; no llegó a PostgreSQL ni aplicó migraciones. No se saltaron preflight/backup.

Siguiente paso conforme a la autorización E5: desde la terminal con acceso, `make db-migrate-check`, después `make db-migrate` si el precheck es satisfactorio; el wrapper realiza respaldo/preflight/upgrade. Ante cualquier fallo, detenerse y conservar la salida sanitizada. Después ejecutar la suite E5 completa sin -k, repetir el precheck y las comprobaciones de readiness del procedimiento del repositorio.

Dictamen global E5: **NO APROBADA** mientras falten instalación/comprobaciones correspondientes. La integración sintética queda **VERIFICADA** en su alcance. No se modificó código ni se inició E6 mediante este registro.
