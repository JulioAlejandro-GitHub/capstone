# Validación B.3C.2

- `scripts/storage/sql/smear_analysis_delete_inventory.sql`: 15 sentencias permitidas, rollback final; SHA-256 `3874c530f96dd066844056b77ffd26b3b8e2b9e79c4de9c296cd79dcbd68fa4f`.
- `scripts/storage/sql/smear_analysis_lineage_lookup.sql`: 8 sentencias permitidas, rollback final; SHA-256 `e2b543af3f9cb70a2e1d3b228aeb38869e65ca8b13818b5b8e659016899e4d84`.
- 2.388 archivos legacy: SHA-256, tamaño y mtime sin cambios.
- 22 blobs del índice Git: 3.920.544 bytes (git cat-file --batch-check); coincide con los archivos del working tree.
- docker compose config --quiet: PASS.
- git diff --check: PASS (complementado por revisión de whitespace de archivos nuevos).
- PostgreSQL READ ONLY: on; 184 validaciones PASS; 5.547 segundos; ROLLBACK.
- Linaje con NULL: 0/0/0 filas; IDs reales de análisis/muestra/historial: 70/54/70 filas, un análisis y una muestra por resultado.
- Fingerprints clínicos iguales entre las dos últimas ejecuciones.
- No se creó template de eliminación, ni se ejecutaron pruebas mutantes.
