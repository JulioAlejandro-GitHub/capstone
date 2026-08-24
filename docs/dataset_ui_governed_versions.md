# Dataset UI gobernada

La ruta existente `/modelo-ia/dataset?datasource=malaria` conserva el menú **Modelo
IA → Dataset**, pero ya no presenta `malaria_physical_split` ni sus counts legacy. El
filesystem y las filas históricas permanecen intactos para compatibilidad.

## API y fuente

La pantalla usa únicamente dos endpoints GET protegidos por `datasets.read`:

- `GET /api/datasets?datasource=malaria`: lista resumida, ordenada por creación reciente.
- `GET /api/datasets/{dataset_version_id}?datasource=malaria`: dataset, distribución,
  integridad, validación, materialización, lineage, lifecycle y runs relacionados.

PostgreSQL es la fuente de verdad. Los counts salen de `dataset_split_statistics`, los
12 checks de `dataset_split_validation_checks`, el attempt de
`dataset_materializations`, los fingerprints de `methodology_json.freeze_contract` y
las ejecuciones exclusivamente de `runs.dataset_version_id`. El adapter llama al
resolver canónico de trainability/materialización de `malaria_dataset_split_project`;
React no calcula estados científicos ni recorre archivos.

## Interfaz

`DatasetVersionCard` soporta múltiples versiones y muestra primero nombre, semver,
lifecycle, trainability, pacientes, imágenes, distribución y readiness. El detalle usa
accordions semánticos para resumen, distribución, integridad patient-disjoint,
validación, materialización, fingerprints y ejecuciones. IDs, hashes completos y root
relativo quedan subordinados como detalles técnicos copiables.

Una versión FROZEN no muestra edición ni configuración científica. Como actualmente no
existe una pantalla gobernada para crear TRAIN, no se inventó un flujo paralelo de “Usar
en entrenamiento”. El enlace “Ver ejecuciones” transporta `dataset_version_id` como
contexto en la URL, pero la pantalla Ejecuciones vigente sólo implementa los filtros
`run` y `modelo`: por ahora el parámetro no reduce esa lista. La relación autoritativa
por versión es la tabla de ejecuciones incluida en el propio detalle del Dataset. La
versión v1 ya presenta allí los runs que tienen ese UUID persistido; los runs históricos
con `dataset_version_id IS NULL` no se reinterpretan como v1.

La página incluye loading de lista/detalle, retry de errores, estados vacíos, tablas con
scroll existente, accordions navegables y adaptación móvil. Las pruebas cubren contrato
PostgreSQL, RBAC, 404/datasource, counts oficiales, ausencia visual de counts legacy,
FROZEN/TRAINABLE, validación, READY/PASS, lineage, consulta de runs vinculados y el
texto de estado vacío. No existe todavía una prueba de filtrado de Ejecuciones por
`dataset_version_id`, porque ese filtro aún no está implementado.
