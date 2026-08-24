# Versiones de runtime

- Python 3.12: API y `malaria_dl`. Es compatible con TensorFlow 2.17.1; Python
  3.14 local no es runtime soportado para ML. No existe un worker operativo;
  uno futuro deberá declarar y validar su runtime por separado.
- PostgreSQL 17 local es el runtime oficial de desarrollo y del gate de
  integración. Los entrypoints Docker opcionales fijan `postgres:17.9`,
  pero no forman parte del gate oficial.
- Node.js 22 LTS y npm 10, declarados en `.nvmrc` y `package.json`.

Las dependencias backend están acotadas por major. TensorFlow permanece fijado. `tensorflow-metal` es específico de macOS y no se instala en el job Linux de fundación salvo suite ML que lo permita.
