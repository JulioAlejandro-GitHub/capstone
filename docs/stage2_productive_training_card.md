# Tarjeta del modelo productivo para Etapa 2

## Regla de elegibilidad

Un TRAIN es elegible cuando su estado es `completed` y existe al menos un EVALUATE `completed` unido mediante `run_lineage.relationship_type = evaluates_checkpoint_from`.

EXPLAIN se conserva como evidencia asociada, pero no participa en la elegibilidad. Si existen varios EVALUATE completados se utiliza el más reciente por `finished_at`, luego `created_at` y finalmente UUID. Un EVALUATE de otro TRAIN no puede entrar en la consulta.

La respuesta distingue:

- `eligible_for_stage2_production`: regla funcional TRAIN + EVALUATE;
- `technical_blockers`: problemas que la preparación automática debe resolver o reportar;
- `is_stage2_production`: estado derivado del deployment activo;
- `production_state`: `not_eligible`, `eligible` o `active`.

## Fuente de verdad

No existe una bandera visual independiente. “Productivo Etapa 2” se deriva de:

- `deployed_model_versions.environment = production`;
- `alias = champion`;
- `status = active`;
- `metadata.production_scope = stage2_technical`.

La restricción de base y la activación transaccional conservan un solo champion activo. El deployment anterior queda inactivo y disponible para rollback.

## Artifact inmutable

La publicación reutiliza `Stage2ModelAvailabilityService`:

1. verifica el artifact fuente y SHA-256;
2. copia atómicamente a `releases/production/<modelo>/<model_version_id>/model.keras`;
3. registra el artifact de paquete;
4. escribe manifest, preprocessing, class mapping, firmas, threshold y checksum;
5. conserva el artifact y la model_version originales;
6. ejecuta smoke e inferencia de control antes de activar.

El frontend solo muestra nombre lógico, model version y SHA abreviado; nunca expone el path físico.

La convención permanece:

- `0 = uninfected`;
- `1 = parasitized`;
- `positive_class = 1`;
- `positive_label = parasitized`;
- `score_name = probability_parasitized`.

Si no existe threshold calibrado, el servicio registra `0.5` como threshold operativo no clínico y conserva su procedencia.

## Tarjeta visual

Toda tarjeta TRAIN productiva recibe:

- `training-card--stage2-production`;
- fondo semántico suave;
- borde verde;
- icono de confirmación;
- badge “Productivo Etapa 2”;
- texto “Modelo activo e inmutable”;
- destino `production / champion`.

Los colores se centralizan en tokens `--stage2-production-*`. El estado no depende solo del color.

La sección Liberación muestra únicamente estado resumido y un enlace real “Ver detalle”. El texto del enlace no cambia.

## Routing

- Con deployment: `/modelo-ia/despliegues/:deploymentId?datasource=malaria`.
- Sin deployment: `/modelo-ia/ejecuciones/:trainingRunId/liberacion?datasource=malaria`.

El detalle carga por ID, conserva datasource, tiene URL copiable y no usa `location.state`.

## Publicación

El detalle de liberación muestra TRAIN, EVALUATE utilizado, EXPLAIN opcionales, model version y scope. “Publicar para Etapa 2” abre una confirmación con responsable, motivo y checkbox explícito.

La llamada es idempotente. Si el deployment ya está activo devuelve las mismas identidades sin copiar ni crear otra versión.

## Baja, reactivación y reemplazo

La administración se mantiene en Despliegues:

- “Dar de baja” cambia el deployment técnico activo a inactivo;
- “Reactivar como productivo” usa la activación gobernada;
- publicar otro modelo desactiva transaccionalmente el champion anterior;
- no se eliminan TRAIN, EVALUATE, model version o artifact.

## Rollback

Se conserva la convención existente: el rollback crea una revisión pendiente basada en una versión histórica y exige verificación antes de activarla. No se sobrescribe ni reactiva silenciosamente una revisión histórica. Esto preserva inmutabilidad y auditoría.

## Endpoints

- `GET /api/training-runs/{id}/stage2-release-status`
- `POST /api/training-runs/{id}/publish-technical-production`
- `GET /api/deployments`
- `GET /api/deployments/{id}/readiness`
- `POST /api/deployments/{id}/deactivate`
- `POST /api/deployments/{id}/activate`
- `POST /api/deployments/{id}/rollback`

## Pruebas

- Elegibilidad unitaria con TRAIN/EVALUATE y EXPLAIN ausente.
- Contratos frontend de acción única, estilo, accesibilidad, routing y confirmación.
- Build TypeScript.
- E2E idempotente sobre el TRAIN real `371a9e75-…`.
- Verificación de un único deployment `production/champion/stage2_technical`.
