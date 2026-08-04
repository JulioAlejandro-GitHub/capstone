# ADR-021: inferencia Etapa 2 basada en publicación

- Estado: Aceptado
- Fecha: 2026-08-04
- Alcance: publicación, resolución de modelo y clasificación celular
- Relacionado: ADR-002, ADR-004, ADR-009, ADR-015 y ADR-020

## Contexto

El flujo previo exigía simultáneamente una publicación activa y un deployment
`stage2/default`. Esa doble autoridad permitía que una versión correctamente
publicada no fuese utilizable, obligaba a reconciliar dos ciclos de vida y
convertía un concepto legacy de deployment en identidad de cada nueva
inferencia.

## Decisión

1. La única regla de elegibilidad y publicación es `TRAIN completed` más su
   `EVALUATE completed`, asociado por `evaluates_checkpoint_from`.
2. La identidad de una inferencia nueva es una
   `stage2_model_publication` activa. El resolver implícito exige exactamente
   una publicación activa; cero o varias bloquean de forma explícita.
3. La publicación no valida ejecutabilidad. Al iniciar inferencia se validan
   artefacto y checksum, framework/formato, firmas, preprocessing, mapping,
   input shape, threshold y calibración. No se reinterpreta esa validación como
   elegibilidad de publicación.
4. Cada run nuevo congela un snapshot esquema v2 con
   `stage2_publication_id` y un objeto `stage2_publication`; no requiere
   `production_model_id` ni `stage2/default`.
5. Runs y snapshots esquema v1 conservan su deployment y siguen siendo
   legibles/reproducibles. No se reescriben registros históricos.
6. La baja/reactivación de publicaciones conserva eventos append-only. No hay
   fallback a último TRAIN, última publicación, checkpoint suelto o threshold
   `0.5`.

## Consecuencias

Publicar habilita el modelo para que el boundary de inferencia intente validar
su contrato técnico, sin una segunda acción de deployment. La disponibilidad
de catálogo y la ejecutabilidad siguen siendo conceptos separados; un modelo
puede estar publicado y fallar de forma segura al cargarlo. Para selección
implícita debe existir una sola publicación activa.

La revisión Alembic `20260804_01` hace nullable el deployment legacy en
`cell_classification_runs`, agrega la identidad/índice por publicación y acepta
snapshots v1 o v2 mediante un trigger estricto. El downgrade se rechaza si ya
existen runs v2.

## Relación con decisiones anteriores

Este ADR **supersede parcialmente**:

- ADR-002, sólo en la obligación de que `stage2/default` sea la fuente de
  selección implícita y referencia necesaria de una publicación;
- ADR-020, sólo en sus decisiones 1 y 2 y en la consecuencia que exigía un
  deployment para inferir.

Permanecen vigentes el catálogo auditable, la validación fail-closed, la
separación detector/clasificador, snapshots determinísticos, predicciones
automáticas inmutables, revisión humana append-only, Grad-CAM manual y el
carácter no diagnóstico.
