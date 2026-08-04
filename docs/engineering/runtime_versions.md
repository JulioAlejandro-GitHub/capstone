# Versiones de runtime

- Python 3.12: API, `malaria_dl`, migraciones y pruebas mediante
  `malaria_dl_local_project/.venv`. Python 3.14 no es runtime soportado para ML.
- PostgreSQL 17 local para desarrollo, integración y demo.
- Node.js 22 LTS y npm 10, declarados en `.nvmrc` y `package.json`.

Las dependencias backend están acotadas por major. TensorFlow permanece fijado.
`tensorflow-metal` es específico de macOS y no se instala en el job Linux.
