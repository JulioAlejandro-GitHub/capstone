# Runbook simplificado: Patient Split de malaria

## Objetivo

Construir una versión gobernada del dataset de malaria:

```text
DRAFT → GENERATED → VALIDATED → READY/PASS → FROZEN/TRAINABLE
```

PostgreSQL es la fuente de verdad. No modificar estados con SQL ni corregir la
materialización moviendo archivos manualmente.

## 1. Confirmar la instancia PostgreSQL

El CLI y el backend deben usar la misma base de datos. 

> [!WARNING]
> **Conflicto de Puertos en macOS**: Si tienes instalado PostgreSQL vía Homebrew, este podría estar escuchando en `127.0.0.1:5432` en el host, interceptando las llamadas del CLI e impidiendo que este se conecte al contenedor Docker (`capstone_db`).

Para validar a qué instancia te estás conectando, ejecuta el paso de auditoría y revisa el campo `postgres_version` en la respuesta:
- **Docker (Esperado)**: Debería contener `Debian` o `linux-gnu`.
- **Homebrew (Incorrecto para el pipeline)**: Contendrá `Homebrew` o `apple-darwin`.

Si detectas que estás conectado a la instancia local de Homebrew, detén su servicio para liberar el puerto `5432` en el host:
```bash
# Intenta detener el servicio de Homebrew
brew services stop postgresql@17

# Si falla con errores Ruby o launchd lo reinicia automáticamente:
launchctl unload ~/Library/LaunchAgents/homebrew.mxcl.postgresql@17.plist
```

Una vez liberado el puerto, las conexiones a `127.0.0.1:5432` irán al contenedor de Docker.

La versión oficial es:

```text
d8c0cab5-09dd-597f-9de7-7ca01aee2ec2
Malaria Patient Split v1
```

Si ya está `FROZEN` en la base destino, no ejecutar nuevamente el pipeline. Conectar el backend a esa base o migrarla mediante backup/restore verificado.

## 2. Precondiciones

Desde la raíz de `capstone`:

```bash
docker compose up -d db backend frontend
docker compose ps
```

Verificar Alembic con las credenciales reales del volumen:

```bash
docker exec capstone_db psql -U <usuario> -d <database> -Atc \
  'SELECT version_num FROM alembic_version;'
```

Resultado esperado:

```text
20260812_02
```

También deben existir:

- las 27.558 imágenes originales;
- los CSV oficiales de Patient-ID;
- espacio para una nueva materialización;
- acceso exclusivo al pipeline durante la ejecución.

## 3. Preparar el CLI

```bash
cd malaria_dataset_split_project
export PYTHONPATH=src
export DATABASE_URL='postgresql+psycopg://<usuario>:<password>@127.0.0.1:5432/<database>'
SPLIT_PYTHON=../malaria_dl_local_project/.venv/bin/python

"$SPLIT_PYTHON" -m malaria_split.cli --help
```

Usar `127.0.0.1` solamente cuando el CLI se ejecute directamente desde macOS.

## 4. Auditorías read-only

```bash
"$SPLIT_PYTHON" -m malaria_split.cli audit-current-split
"$SPLIT_PYTHON" -m malaria_split.cli audit-patient-identity
"$SPLIT_PYTHON" -m malaria_split.cli audit-system-contracts
```

Continuar únicamente si se confirman:

- 27.558 imágenes;
- 201 pacientes;
- 100 % de cobertura Patient-ID;
- cero conflictos de identidad;
- esquema Alembic `20260812_02`.

El leakage del split físico legacy es esperado; este pipeline crea el reemplazo
patient-disjoint.

## 5. Crear la versión DRAFT

Primero simular:

```bash
"$SPLIT_PYTHON" -m malaria_split.cli bootstrap-malaria-v1 --dry-run
```

Si devuelve `PASS`, aplicar y auditar:

```bash
"$SPLIT_PYTHON" -m malaria_split.cli bootstrap-malaria-v1
"$SPLIT_PYTHON" -m malaria_split.cli audit-scientific-bootstrap
```

Esperado: `DRAFT`, 27.558 source records y cero assignments.

## 6. Generar y persistir el split

Auditar perfiles y generar el candidato reproducible:

```bash
"$SPLIT_PYTHON" -m malaria_split.cli audit-patient-profiles-v1 \
  --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2

"$SPLIT_PYTHON" -m malaria_split.cli generate-patient-split-v1 \
  --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
  --dry-run
```

El candidato debe ser válido, determinista y sin hard-constraint violations.

Ensayar la transacción:

```bash
"$SPLIT_PYTHON" -m malaria_split.cli persist-patient-split-v1 --rehearse
```

Debe hacer rollback y conservar `DRAFT` con cero assignments. Después aplicar:

```bash
"$SPLIT_PYTHON" -m malaria_split.cli persist-patient-split-v1 --apply
```

Esperado: `GENERATED` y 27.558 assignments.

| Split | Imágenes | Pacientes |
|---|---:|---:|
| train | 22.180 | 161 |
| val | 2.693 | 20 |
| test | 2.685 | 20 |

## 7. Validar

```bash
"$SPLIT_PYTHON" -m malaria_split.cli validate-patient-split-v1
```

Esperado:

- status `VALIDATED`;
- 12/12 checks `PASS`;
- cero overlap de pacientes;
- ambas clases presentes en train, val y test.

## 8. Materializar

Revisar `config/current_split.yaml` y ejecutar:

```bash
"$SPLIT_PYTHON" -m malaria_split.cli materialize-patient-split-v1 \
  --config config/current_split.yaml
```

> [!WARNING]
> **Conflicto de Directorio Existente (`FINAL_ROOT_EXISTS_WITHOUT_READY_PASS`)**:
> Si estás corriendo esto en una base de datos nueva/limpia pero la carpeta física de la versión ya existe en el disco (`malaria_dl_local_project/data/malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`), el comando fallará indicando que la carpeta existe en el disco pero no está registrada como `READY`/`PASS` en la base de datos.
>
> **Solución**: Mueve la carpeta física existente antes de ejecutar el comando para permitir que el script la vuelva a crear y registrar:
> ```bash
> mv ../malaria_dl_local_project/data/malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 ../malaria_dl_local_project/data/malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2.bak
> # Y tras una materialización exitosa, puedes borrar la copia de respaldo:
> rm -rf ../malaria_dl_local_project/data/malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2.bak
> ```

Esperado:

- materialización `READY`;
- reconciliación `PASS`;
- 27.558 archivos encontrados;
- cero archivos faltantes o inesperados;
- 27.558 SHA-256 match y cero mismatch.

## 9. Congelar

```bash
"$SPLIT_PYTHON" -m malaria_split.cli freeze-patient-split-v1
```

Resultado final obligatorio:

```text
status=FROZEN
trainable=true
trainability_reasons=[]
```

Una versión `FROZEN` es inmutable. Los cambios futuros requieren una nueva versión.

## 10. Verificación final

Consultar PostgreSQL:

```sql
SELECT id,name,semantic_version,status,source_record_count,
       generated_at,validated_at,frozen_at
FROM dataset_versions
ORDER BY created_at DESC;

SELECT dataset_version_id,status,reconciliation_status,record_count,relative_root
FROM dataset_materializations
ORDER BY started_at DESC;
```

Abrir:

```text
http://localhost/modelo-ia/dataset?datasource=malaria
```

La UI debe mostrar `FROZEN`, `TRAINABLE`, 201 pacientes, 27.558 imágenes, 12/12 checks
y materialización `READY/PASS`.

## Cuándo detenerse

Detener el pipeline si:

- el CLI y el backend apuntan a bases diferentes;
- un dry-run o auditoría no devuelve `PASS`;
- el rehearsal no revierte todas las escrituras;
- aparece `*_STATE_CONFLICT`;
- validation no obtiene 12/12 checks;
- reconciliation presenta missing, mismatch u overlap;
- la versión oficial ya está `FROZEN`.

No borrar evidencia ni forzar estados para continuar.
