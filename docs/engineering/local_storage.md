# Storage local

`STORAGE_ROOT=./var/storage` se resuelve desde la raíz del repositorio.

`microscopy-images/{subject_uuid}/{sample_uuid}/{slide_uuid}/{image_uuid}/{sha256}.{ext}`

La clave guardada es relativa. Se rechazan rutas absolutas, `..`, bytes nulos y
symlinks; se verifica containment, se evita overwrite y se aplican permisos
restrictivos. El filename sólo se conserva como metadata sanitizada.
