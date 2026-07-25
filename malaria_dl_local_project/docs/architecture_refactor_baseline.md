# Línea base del refactor arquitectónico

Fecha: 2026-07-24.

El entorno válido es `malaria_dl_local_project/.venv` con Python 3.12.13.
Antes de migrar, `compileall` fue correcto y la suite ejecutó 357 pruebas
correctas con 1 omitida. El Python global 3.14 no contiene NumPy, TensorFlow,
SQLAlchemy, Pillow ni scikit-learn; esos errores son del entorno, no del código.

No se ejecutó entrenamiento ni se escribió en PostgreSQL. La salida confirmó
`0=uninfected`, `1=parasitized` y `raw_model_score=probability_parasitized`.

