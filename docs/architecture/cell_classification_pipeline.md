# Pipeline de clasificación celular productiva

## Secuencia

```text
detection run terminal
  -> resolver una publicación Stage 2 activa
  -> validar contrato técnico y checkpoint al iniciar inferencia
  -> congelar manifest y model snapshot
  -> cargar modelo una vez
  -> preprocess + inferencia por batches
  -> normalizar sigmoid/softmax según mapping
  -> aplicar threshold publicado
  -> persistir predicciones y estados parciales
  -> crear resumen automático experimental
  -> revisión y Grad-CAM manual
```

El resolver actual parte de exactamente una publicación Stage 2 activa. No
requiere un deployment para runs nuevos: congela un snapshot publication-first
esquema v2. Los snapshots esquema v1 con deployment se conservan para lectura
histórica. Cero o varias publicaciones activas bloquean el inicio; tampoco se
elige “latest”.

La ejecución HTTP usa el threadpool de FastAPI. No hay worker, broker, polling ni
retry automático. Los errores de modelo, mapping, preprocessing o checksum son
terminales. Un crop individual fallido no elimina resultados válidos y cierra el
run como `completed_with_warnings`.

## Entradas congeladas

El manifiesto se ordena por secuencia de imagen, `cell_index` e ID. Incluye
detección, crop, checksum, dimensiones, detector, última revisión regional,
elegibilidad y motivo de exclusión. Su JSON canónico usa claves ordenadas,
separadores compactos y SHA-256.

Se excluye una detección cuya última revisión efectiva sea `rejected`, cuyo crop
no exista o cuya integridad no coincida. `accepted`, `needs_attention` y sin
revisión son elegibles.

## Idempotencia y fallos

La equivalencia v2 combina detection run, publicación, checkpoint, versión de
modelo, versión de inferencia y manifest. Un run `failed` nunca se sobrescribe:
el retry manual crea otro con `retry_of_run_id`.

Las etapas durables emiten eventos y auditoría. No se persisten píxeles, tokens,
PII ni paths absolutos en eventos o snapshots.

El agregado persistido se expone como `automatic_summary`; la revisión produce
un `reviewed_summary` derivado. El contrato canónico de desglose por imagen es
`{"images": [...]}` y queda protegido por la cadena Alembic
`20260728_01 → 20260728_02 → 20260728_03 → 20260804_01`.
