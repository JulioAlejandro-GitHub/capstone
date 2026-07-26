# Versiones de runtime

- Python 3.12: API, `malaria_dl` y futuro worker. Es compatible con TensorFlow 2.17.1; Python 3.14 local no es runtime soportado para ML.
- PostgreSQL 17 (`postgres:17-alpine`) para test y demo.
- Node.js 22 LTS y npm 10, declarados en `.nvmrc` y `package.json`.

Las dependencias backend están acotadas por major. TensorFlow permanece fijado. `tensorflow-metal` es específico de macOS y no se instala en el job Linux de fundación salvo suite ML que lo permita.
