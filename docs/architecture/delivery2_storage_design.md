# Diseño de almacenamiento — Entrega 2

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No; diseño objetivo previo a `LocalStorage`.
> **Snapshot:** Entrega 2 / Architecture Baseline v1.1.

## Decisión

`StorageProvider` es el único acceso nuevo a bytes. La implementación MVP es `LocalStorageProvider`; PostgreSQL conserva URI lógica, checksum, MIME, tamaño, owner y auditoría, nunca imágenes `BYTEA`. Los servicios actuales `backend_api/app/services/artifacts.py`, `malaria_dl/common/paths.py` y releases se adaptarán gradualmente detrás del provider.

## Interfaz conceptual

```text
put_original(stream, owner, mime, expected_size?, idempotency_key) -> ArtifactMetadata
put_artifact(stream, owner, artifact_type, run_id, mime, provenance) -> ArtifactMetadata
get_metadata(storage_uri) -> ArtifactMetadata
open(storage_uri, mode="rb") -> BinaryIO
exists(storage_uri) -> bool
verify_checksum(storage_uri, sha256) -> VerificationResult
create_access_reference(storage_uri, principal, expires_in) -> opaque URL/reference
delete_regenerable_artifact(storage_uri, actor, reason) -> Tombstone
list_artifacts(owner, filters, cursor) -> Page
```

Todas las operaciones validan URI/owner; `put_*` calcula SHA-256 mientras escribe a temporal, `fsync` cuando sea viable, renombra atómicamente y sólo después permite registrar disponibilidad. `put_original` es create-only. `put_artifact` nunca sobrescribe: regeneración crea UUID/URI nuevo.

## Metadata

`artifact_id`, `storage_uri`, `storage_provider`, `artifact_type`, `owner_entity_type`, `owner_entity_id`, `run_id`, `mime_type`, `size_bytes`, `checksum_sha256`, `created_at`, `created_by`, `immutability_class` (`original|critical_derived|regenerable`), `status`, `provenance`, `correlation_id`. Rutas físicas son internas y no forman parte de API.

## Layout local

```text
storage/subjects/{subject_uuid}/samples/{sample_uuid}/images/{image_uuid}/
  original/{artifact_uuid}
  quality/{artifact_uuid}
  tiles/{artifact_uuid}
  detections/{artifact_uuid}
  crops/{artifact_uuid}
  explainability/{artifact_uuid}
  reports/{artifact_uuid}
```

Se usan UUID internos aleatorios. Ningún patient ID, nombre, identificador externo o label clínico legible aparece en rutas. El provider traduce `storage://local/{artifact_uuid}`; el layout es detalle privado y migrable.

## Seguridad

- Canonicalización y allowlist de raíz; rechazo absoluto de `..`, symlinks fuera de raíz, rutas absolutas y separadores no canónicos.
- Upload streaming con límites configurados de bytes/píxeles/dimensiones y timeout.
- MIME declarado se contrasta con firma y decodificación segura; extensión no decide MIME.
- Referencias de acceso son opacas, autorizadas, cortas y auditadas; nunca devuelven path físico.
- Original y artefactos críticos: `ON DELETE RESTRICT` lógico. Sólo regenerables pueden borrarse con permiso y tombstone.
- Checksum se verifica al ingreso, antes de inferencia y durante reconciliación.

## Inmutabilidad y consistencia

El filesystem y PostgreSQL no forman una transacción distribuida. Se usa patrón prepare/finalize:

1. Escribir temporal y calcular checksum.
2. Mover a URI final create-only.
3. Insertar `artifact_record` status `available`.
4. Si falla DB, reconciliador detecta artifact sin registro por manifest lateral interno.
5. Si falta artifact para registro available, marcar `missing`; nunca reemplazar silenciosamente.

Originales no se borran en MVP. Artefactos regenerables requieren que provenance suficiente exista. Reports, predictions y explanations históricos son versionados; su artifact puede archivarse, no mutarse.

## Quality reject

La imagen original se conserva. Assessment y artefactos de QC quedan en `quality/`. No se crean directorios/artefactos de detection/crops para esa evaluación rechazada.

## Migración futura

`storage_uri`, no path, es identidad. Un futuro provider MinIO/S3 implementa la misma interfaz, mantiene artifact UUID/checksum y puede copiar bytes con estado `migrating`; una tabla de locator/provider permite dual read durante transición. Ningún contrato API cambia.
