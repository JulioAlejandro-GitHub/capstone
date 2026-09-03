# Storage local

El runtime Docker usa un único volumen administrado por Compose:

```text
scientific_storage → /app/var/storage
```

Compose fija `STORAGE_PROVIDER=local` y `STORAGE_ROOT=/app/var/storage`. Este es
un contrato de runtime, no una ruta libremente configurable ni un bind del
host. El backend exige que `STORAGE_ROOT` exista en el entorno y sea una ruta
absoluta; la validación no crea el directorio. Las pruebas deben inyectar una
ruta absoluta dentro de su directorio temporal.

El Dockerfile crea el mountpoint vacío y con ownership del usuario no root
`capstone`. Los roots históricos `var/storage` y `backend_api/var/storage`
quedan fuera del build context y no se montan. Los 22 binarios ya rastreados
son deuda conocida y se retirarán del índice en Storage B.4; esta fase no los
mueve ni elimina.

`microscopy-images/{subject_uuid}/{sample_uuid}/{slide_uuid}/{image_uuid}/{sha256}.{ext}`

La clave guardada es relativa. Se rechazan rutas absolutas, `..`, bytes nulos y
symlinks; se verifica containment, se evita overwrite y se aplican permisos
restrictivos. El filename sólo se conserva como metadata sanitizada.

## Contrato de lectura

Construir `LocalStorage`, `CellCropStorage` o `CellExplanationStorage` no crea
el root, `.staging` ni namespaces. `resolve_verified` valida una key POSIX
relativa, containment y ausencia de symlinks; exige archivo regular, tamaño
exacto y SHA-256 hexadecimal de 64 caracteres. El checksum se calcula por
streaming desde un descriptor `O_NOFOLLOW` cuando la plataforma lo soporta.

Los errores distinguen clave insegura, ausencia, tipo inválido, tamaño y
checksum. Los endpoints traducen estos errores sin revelar paths físicos. Los
listados no leen archivos ni calculan checksums.

## Contrato de escritura y cleanup

Sólo `stage`, `stage_bytes`, `create_staging_directory` y `promote` preparan
directorios. Los temporales reciben nombres impredecibles y permisos `0600`;
los directorios creados usan `0700`. La promoción create-only usa un hard link
atómico dentro del mismo filesystem y luego retira el temporal, por lo que no
puede reemplazar un destino preexistente.

El cleanup acepta boundaries explícitos, nunca elimina `STORAGE_ROOT`, el
namespace ni `.staging`, y sólo actúa sobre paths registrados como creados por
la instancia de la operación.

`model-explanations` no es contenido clínico. Las nuevas explicaciones de
modelos se escriben bajo `ARTIFACTS_ROOT/model-explanations` y usan staging
separado. Las referencias históricas bajo `var/storage/model-explanations` se
mantienen únicamente para lectura; no se reinterpretan ni se mueven en B.2B.1.
