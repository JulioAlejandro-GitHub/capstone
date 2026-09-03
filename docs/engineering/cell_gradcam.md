# Grad-CAM por célula

Grad-CAM se ejecuta únicamente por acción manual sobre una predicción. La
clasificación no lo genera automáticamente ni carga todas las explicaciones en
la galería.

El adapter reutiliza el helper matemático canónico de explainability: localiza
la última capa convolucional conectada, calcula gradientes, normaliza el mapa y
produce dos derivados:

```text
cell-explanations/{analysis_run_id}/{classification_run_id}/
  {cell_detection_id}/gradcam_heatmap.png
cell-explanations/{analysis_run_id}/{classification_run_id}/
  {cell_detection_id}/gradcam_overlay.png
```

Se usa staging bajo `.staging/cell-explanations`, promoción create-only y
checksum independiente. Tanto heatmap como overlay delegan resolución,
integridad, promoción y cleanup en `LocalStorage`. El crop no se modifica.

La allowlist de persistencia admite únicamente claves relativas con UUID bajo
`cell-explanations/` y los nombres exactos `gradcam_heatmap.png` y
`gradcam_overlay.png`. No se admiten paths absolutos, traversal, symlinks,
objetos fuera de `STORAGE_ROOT` ni binarios en PostgreSQL. Las claves no se
devuelven en JSON público: el acceso se realiza sólo por los endpoints PNG
autenticados.

Si el framework, capa o gradientes no son compatibles, el estado es
`unsupported`; si ocurre un fallo técnico, es `failed`. Ninguno cambia la
predicción ni el summary. Reintentar un fallo requiere `retry=true` explícito.
Una explicación `generated` equivalente se reutiliza.

`scripts/storage/reconcile_cell_explanations.py` es dry-run por defecto y reporta registros sin
archivo, huérfanos, checksum/tamaño distintos, paths inseguros, symlinks y
staging residual.

Las explicaciones de casos de modelos (`model-explanations`) son artefactos no
clínicos distintos de estas explicaciones celulares. Desde Storage B.2B.1 sus
nuevas escrituras usan `ARTIFACTS_ROOT/model-explanations` y un staging propio;
no comparten `STORAGE_ROOT` ni `.staging` clínico. Las referencias históricas
siguen siendo legibles sin migrar archivos o filas.
