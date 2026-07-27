# Microscopy analysis runs

Un `microscopy_analysis_run` pertenece a sujeto, caso, muestra, frotis y lote de
ingesta, y nunca a un entrenamiento. Su código público es `ANL-` más 8 caracteres
hexadecimales aleatorios. Al crearlo se copian identidad, secuencia, SHA-256,
tamaño y dimensiones de cada entrada a `microscopy_analysis_run_images`.

El manifiesto JSON se ordena por secuencia e ID, usa claves ordenadas y
separadores compactos; `input_manifest_sha256` es el SHA-256 UTF-8 de ese JSON.
No se añaden imágenes a un run existente. La unicidad de lote, perfil, versión,
algoritmo y manifiesto evita duplicados accidentales.
