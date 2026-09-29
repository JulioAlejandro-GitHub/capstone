# E10.10.5C — Preflight de adopción

Implementado y probado con fixtures; **no ejecutado contra PostgreSQL en C**. No existe descriptor D aprobado ni identidad de una copia de adopción certificada en esta entrega. Los descriptores de B no autorizan este ejecutor.

| Orden | Comprobación | Bloqueo / efecto |
| --- | --- | --- |
| 1 | Etapa D y Gate C expresamente aprobado, `copy_only`, `writers_fenced` | Rechazo antes de importar drivers, inspeccionar Docker o conectar. |
| 2 | UUID aislamiento; container ID completo; base/volumen con prefijo aislado; puerto independiente 1024–65535 excluyendo 5432/5433 | Rechaza nombres ambiguos, puertos operativos y descriptor parcial. |
| 3 | URL explícita psycopg, loopback 127.0.0.1, puerto/base/rol exactos, sin parámetros ni fragmento | No lee .env ni configuración de la aplicación. No muestra contraseña. |
| 4 | OID y system identifier fijados; cluster distinto del origen; hashes de backup, mapping, inventario y esquema | No acepta origen como destino ni bindings distintos de los revisados. |
| 5 | Backup local de instalación aislada, bytes SHA-256 iguales al descriptor | Sin backup íntegro no inspecciona ni conecta. El origen del backup se acredita en D; un hash no prueba procedencia por sí solo. |
| 6 | Guardas Docker de B: contenedor vivo, label, volumen exclusivo, puerto loopback y mounts/privilegios aislados | Sólo metadatos; ninguna preparación o arranque automático. |
| 7 | current/session user, base/OID/owner, cluster, PostgreSQL 17, lectura/escritura y no recuperación | Registro privado de identidad antes de DDL/DML. |
| 8 | Roles capstone_v2_migrator y capstone_v2_runtime sin SUPERUSER, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS ni membresías | Separación contractual; el ejecutor no concede privilegios administrativos. |
| 9 | Transacción y advisory lock; revisión única exacta; locks exclusivos de las 97 tablas | Timeout 5 s ante locks; no comparte escritores. |
| 10 | Cero otras sesiones de la misma base; gate libre y evidencia de proceso vacía | No acepta campañas/sesiones/intentos activos ni completed aún no verificados. |
| 11 | Siete grupos de esquema legacy idénticos al contrato, incluidos cuerpos de funciones, constraints y triggers habilitados; typmods comprobados | El head por sí solo no acredita forma estructural. |
| 12 | Extensiones y secuencias iguales a Ruta A; propietarios migrador; sin schemas de usuario adicionales | Exige copia preparada correctamente en D; no repara owners o amplía permisos a escondidas. |
| 13 | 22 registros históricos exactos y checksums iguales a archivos locales inmutables; sin faltantes/duplicados | Los SQL sólo se hashean, jamás se ejecutan; 004_seed no se incorpora al ledger de 22. |
| 14 | PK sin duplicados, tres modelos originales, inventario nuevo y SHA-256 igual al autorizado | No presupone que el inventario de E10.10.1 continúa vigente. |
| 15 | E10 canonical bytes, IDs, timestamps, secuencias, epoch/legacy payload y records_hash de sesiones verificadas | No reserializa ni modifica el contenido persistido de los eventos. |
| 16 | Cobertura y bindings científicos completos, cardinalidades y linaje compatibles | Cualquier ambigüedad bloquea antes de transformar. |
| 17 | Snapshot/plan/bindings/delta escritos y fsync antes de primer DDL | Directorio propio 0700 fuera del repositorio; archivos 0600, exclusivos, sin seguir symlink de archivo. |
| 18 | Tras transformación: datos reconciliados, secuencia sin avance y catálogo completo idéntico a Ruta A | Sólo entonces se cambia condicionalmente el head; fallo revierte toda la transacción. |

El esquema autorizado se fija con `digest(schema_signature(catalog))`; el inventario con `digest(preflight(snapshot))`; los bindings con `digest(bindings)`. Estas funciones usan la codificación canónica del adaptador, no `json.dumps` arbitrario. `backup_sha256` es SHA-256 de bytes del archivo. `completed_plan_sha256` es el hash propio del plan sin ese campo. El certificado nativo de B usa la canonicalización de B, separada y comprobada por `certified_catalog()`.

`source_snapshot.json`, `bindings.json`, `plan.json`, `ddl.json`, `preflight_identity.json`, `prepared_receipt.json` y `committed_receipt.json` son evidencia privada de ejecución futura. Un directorio se utiliza una sola vez. La auditoría pública sólo debe contener identidades técnicas autorizadas, conteos, hashes y códigos; nunca filas con contraseñas u otros datos privados.

**Recuperación:** antes de COMMIT se revierte DDL/DML/head. Los archivos fuera de la transacción se conservan para diagnóstico, sin certificar éxito. Si falla el recibo posterior al COMMIT, o se pierde la conexión durante COMMIT, se comprueba la base aislada con identidad y plan originales; no se ejecuta de nuevo a ciegas. Repetición verificada no aplica DDL/DML. Restore real, permisos de preparación y ensayo de pérdida de conexión quedan pendientes de D.
