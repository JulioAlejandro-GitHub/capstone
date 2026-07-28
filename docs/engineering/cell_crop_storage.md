# Storage local de crops celulares

## Contrato de claves

Root configurado:

```text
STORAGE_ROOT=./var/storage
```

Destino:

```text
cell-crops/
  {analysis_run_id}/
  {detection_run_id}/
  {microscopy_image_id}/
  {cell_detection_id}/
  crop.png
```

Staging:

```text
.staging/cell-detection/
  {detection_run_id}/
  {microscopy_image_id}/
  {cell_detection_id}/
  crop.png
```

PostgreSQL guarda únicamente la key POSIX relativa desde `STORAGE_ROOT`, por
ejemplo:

```text
cell-crops/<uuid>/<uuid>/<uuid>/<uuid>/crop.png
```

No guarda paths absolutos, URLs locales, `bytea`, base64 ni overlays.

## Seguridad de resolución

Toda lectura, promoción o reconciliación:

- construye segmentos de destino a partir de UUID del servidor, no de filenames
  del cliente;
- rechaza key vacía/absoluta, `..`, `\0` y escape de root;
- inspecciona cada segmento y rechaza symlinks;
- exige archivo regular cuando `must_exist=true`;
- no sigue symlinks durante limpieza;
- crea directorios privados y archivos con permisos restrictivos;
- nunca sobrescribe un destino existente.

El endpoint de contenido vuelve a validar confinement y tipo de archivo. Que la
key provenga de PostgreSQL no la convierte en confiable.

## Generación

1. Verificar tamaño, SHA-256, formato y dimensiones del original congelado.
2. Mantener el original abierto sólo para lectura.
3. Recortar la caja aceptada con padding limitado por los bordes.
4. Codificar un PNG preservando el modo/píxeles cuando éste es compatible, sin
   overlays ni realce de color/tinción; un modo incompatible falla
   sanitizadamente en vez de convertirlo en silencio.
5. Escribirlo con nombre temporal exclusivo en staging.
6. Vaciar/cerrar el archivo y calcular SHA-256 y bytes sobre la codificación
   final.
7. Reabrir/validar formato PNG y dimensiones esperadas.
8. Preparar metadata `cell_crops`.

El bbox se conserva sin padding. El padding sólo amplía el crop hasta el borde
disponible:

```text
left   = max(0, x - padding)
top    = max(0, y - padding)
right  = min(original_width,  x + width  + padding)
bottom = min(original_height, y + height + padding)
```

No hay resize persistente. Los píxeles usados para segmentación pueden ser una
representación en memoria; el crop se obtiene del raster original orientado, no
de la máscara, luminancia o imagen suavizada.

## Atomicidad y compensación

PostgreSQL y APFS no ofrecen una transacción común. La implementación usa:

- staging privado antes de publicar;
- `os.replace` para promoción atómica de cada archivo dentro del mismo
  filesystem;
- destinos determinísticos y no sobrescribibles;
- una transacción de metadata/eventos/auditoría;
- lista explícita de archivos promovidos para compensación.

Si falla una promoción, se eliminan únicamente temporales y destinos creados por
esa ejecución y la transacción de metadata revierte. Si falla la transacción
después de promover, se compensan esos destinos. Si el proceso termina
abruptamente entre operaciones puede quedar:

- un temporal sin metadata;
- un crop huérfano sin fila;
- excepcionalmente una fila cuyo archivo falta.

Estos estados no se ocultan: el reconciliador los informa. `os.replace` no hace
atómico el lote completo y la documentación no afirma lo contrario.

La transición del run a `failed` y su evento seguro se registra en una
transacción de recuperación separada, después de intentar la compensación. No
se reintenta automáticamente.

## Reconciliación

`scripts/storage/reconcile_cell_crops.py` es dry-run por defecto. Debe comparar:

- filas cuyo archivo falta;
- archivos bajo `cell-crops/` sin metadata;
- keys inseguras o fuera del layout esperado;
- symlinks/no-archivos;
- tamaño, SHA-256, formato o dimensiones divergentes;
- detección aceptada sin su crop;
- crop duplicado para una detección;
- temporales residuales bajo `.staging/cell-detection`.

Un modo correctivo, si se incorpora, exige flag explícito y no puede borrar
originales. La salida no debe imprimir paths absolutos ni datos personales.

## Inmutabilidad del original

El pipeline no abre originales con modo de escritura, no los rota/normaliza en
disco, no agrega boxes y no reemplaza sus archivos. La validación reproduce el
SHA-256 antes y después de las pruebas. El hash del crop no sustituye al hash
del original: ambos pertenecen a artefactos distintos.

## Servicio de contenido

El crop sólo se obtiene mediante
`GET /api/v1/cell-analysis/crops/{crop_id}/content`, con JWT y permiso de
lectura. La respuesta usa `no-store`, `nosniff`, `Content-Length` y ETag. La API
no revela `relative_storage_key` ni permite consultar una key arbitraria.
