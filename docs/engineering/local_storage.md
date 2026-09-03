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
