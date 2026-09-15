# Comandos reales ejecutados — E9.3 ejecutor local (2026-09-15)

## Entorno local (venv dedicado, Python 3.12, macOS arm64)

```bash
cd malaria_dl_local_project
/opt/homebrew/bin/python3.12 -m venv .venv-local-train
.venv-local-train/bin/python -m pip install --upgrade pip -q
.venv-local-train/bin/pip install -q -r requirements.txt psutil==6.1.1
.venv-local-train/bin/pip freeze > requirements-local-train.txt   # + cabecera explicativa
```

Smoke test de plataforma/dispositivo (salida real observada):

```
python 3.12.13
platform macOS-26.5.2-arm64-arm-64bit
machine arm64
tensorflow 2.17.1
numpy 1.26.4
psutil 6.1.1
fastapi 0.141.1
uvicorn 0.53.0
sqlalchemy 2.0.53
psycopg 3.3.5
httpx 0.28.1
gpu_devices []
all_devices [PhysicalDevice(name='/physical_device:CPU:0', device_type='CPU')]
```

## Suite nueva contra PostgreSQL real (esquema desechable), dentro de Docker

```bash
docker compose exec -T -w /app/malaria_dl_local_project \
 -e RUN_LOCAL_EXECUTION_POSTGRES_TESTS=1 -e RUN_STAGE93_GLOBAL_POSTGRES_TESTS=1 \
 -e RUN_STAGE93_CONTROLLED_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 -e TF_CPP_MIN_LOG_LEVEL=3 \
 backend python -B -m pytest -q -p no:cacheprovider \
 tests/test_local_execution_postgres.py -k 'not test_minimal_real_calculation_through_http_agent_and_subprocess'
```

Resultado real (ejecutado 3 veces para descartar inestabilidad en las pruebas de
concurrencia; las 3 corridas dieron el mismo resultado):

```
....................
20 passed, 1 deselected in ~5.2s
```

## Cierre obligatorio: recorrido real en macOS nativo

Requiere que el proceso de pytest nativo (fuera de Docker) pueda abrir el esquema
desechable en el mismo PostgreSQL de Docker. `get_engine()` exige explícitamente que
`DATABASE_URL` use el hostname literal `db` (guardia de seguridad para impedir
conexiones accidentales a otra base) — con autorización expresa del usuario se agregó
un alias temporal en `/etc/hosts` (revertido inmediatamente después de la prueba):

```bash
# Confirmado por el usuario, ejecutado por el usuario (requiere sudo):
echo '127.0.0.1 db # capstone-local-execution-e2e-temp' | sudo tee -a /etc/hosts
```

Ejecución real, nativa, del recorrido completo API → agente → subproceso TRAIN →
checkpoint → API → PostgreSQL:

```bash
cd malaria_dl_local_project
export DATABASE_URL="postgresql+psycopg://julio:root@db:5432/malaria_experiments"
export APP_ENV=development AUTH_MODE=local_jwt ALLOW_INSECURE_LOCAL_AUTH=false
export JWT_SECRET=native-e2e-test-secret-unused JWT_ALGORITHM=HS256
export STORAGE_PROVIDER=local STORAGE_ROOT=/tmp/capstone-native-e2e-storage
export ARTIFACTS_ROOT=/tmp/capstone-native-e2e-artifacts
export MALARIA_DL_PROJECT_ROOT="$(pwd)"
export RUN_LOCAL_EXECUTION_POSTGRES_TESTS=1 RUN_STAGE93_GLOBAL_POSTGRES_TESTS=1 RUN_STAGE93_CONTROLLED_POSTGRES_TESTS=1
export TF_CPP_MIN_LOG_LEVEL=3 PYTHONDONTWRITEBYTECODE=1
.venv-local-train/bin/python -B -m pytest -q -s -p no:cacheprovider \
  tests/test_local_execution_postgres.py::test_minimal_real_calculation_through_http_agent_and_subprocess
```

Resultado real:

```
.
1 passed in 15.79s
```

Este único caso levanta un `uvicorn` real en el proceso de pytest nativo (nunca el
`capstone_backend` en ejecución), lanza `agent.py` como subproceso real (que a su vez
lanza `worker.py` como subproceso real), entrena `custom_cnn` de verdad (1 época,
batch 2, imágenes sintéticas 16×16, sin aumento) con TensorFlow 2.17.1 en CPU nativo de
macOS/arm64, serializa un checkpoint `.keras` real, lo hashea tras el cierre, lo carga
de vuelta con el cargador real (`keras_loader`, subproceso separado), y confirma
`completed`→`verified` leyendo desde una conexión PostgreSQL nueva. El único punto
estructuralmente imposible de ejercer fuera de Linux (`process_table()` escanea
`/proc` para detectar un coordinador Docker vivo) se sustituyó por un stub sólo en este
caso — ese mismo chequeo ya está probado de verdad en Linux por
`test_local_job_blocks_docker_gate_while_held` / `test_docker_gate_blocks_local_claim`.

Reversión inmediata del alias temporal (ejecutada por el usuario):

```bash
sudo sed -i '' '/capstone-local-execution-e2e-temp/d' /etc/hosts
```

Confirmado: `/etc/hosts` quedó exactamente como antes de la intervención.

## Verificación final de no intervención sobre la base real

```bash
docker compose exec -T backend python -B -m alembic current
# -> 20260914_02  (idéntico al estado inicial; la migración 20260915_01 NO se aplicó)

docker compose exec -T backend python -B -c "
from sqlalchemy import text
from src.malaria_dl.persistence.database import get_engine
e = get_engine()
with e.connect() as c:
    c.execute(text('SET TRANSACTION READ ONLY'))
    print(dict(c.execute(text(\"SELECT state, contract_hash FROM experimental_campaigns WHERE id='3acf89b7-dc42-4b7a-8e2a-ca6ea024c344'\")).mappings().one()))
    print(c.execute(text(\"SELECT status FROM runs WHERE id='79f39931-ac71-4bc1-a317-149a975d1f74'\")).scalar_one())
    print(c.execute(text(\"SELECT state FROM train_execution_sessions WHERE run_id='79f39931-ac71-4bc1-a317-149a975d1f74'\")).scalar_one())
    print(dict(c.execute(text('SELECT owner, blocked_reason FROM experiment_execution_gate')).mappings().one()))
"
```

Salida real:

```
campaign {'state': 'paused', 'contract_hash': '02a63b0c76dc600bcb17c7163699abf7dd4e5579643b6adbc783f50d30fcf1ba'}
run status failed
session state failed
gate {'owner': None, 'blocked_reason': 'NEW_CONTAINER_OOM_PAUSE'}
```

Sin cambios respecto al inicio de la sesión. Cero reservas nuevas contra la campaña
real. La tabla `local_execution_jobs` no existe en la base persistente (migración no
aplicada allí).
