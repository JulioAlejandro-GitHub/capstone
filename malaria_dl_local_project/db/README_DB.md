# Persistencia de experimentos ML

La guía canónica de PostgreSQL, bootstrap histórico, Alembic y seguridad está en
[`../../docs/database.md`](../../docs/database.md). Este README sólo resume las
particularidades del tracking ML.

## Configuración única

API, ML, migraciones y pruebas usan el entorno Python 3.12
`malaria_dl_local_project/.venv` y el `.env` privado de la raíz del repositorio.
La única plantilla versionada es `../../.env.example`. No cree un `.env` en este
subproyecto, no configure una segunda URL y no use otra base persistente para
tests.

`DATABASE_URL` debe identificar la base Capstone autorizada. Credenciales, URLs
completas y passwords nunca se documentan ni se confirman en Git.

## Ledger SQL histórico

`db/init/NNN_*.sql` contiene el bootstrap anterior a Alembic. El runner
`scripts/init_db.py`:

- descubre los SQL numerados y los ejecuta en orden;
- registra SHA-256 y metadata en `schema_migrations`;
- omite una migración sólo cuando ID y checksum coinciden;
- reconoce el baseline legacy 001–022 únicamente si comprueba su estructura;
- no ejecuta `alembic stamp` ni `alembic upgrade`.

El tramo de gobierno es 023–029 y se conserva inmutable. Para una base
persistente no ejecute el runner directamente como atajo: use el preflight,
backup y proceso de adopción de [`../../docs/database.md`](../../docs/database.md).

La instalación completa puede verificarse sin alterar `public`:

```bash
cd <PROJECT_ROOT>
make test-fresh-schema
```

Ese gate crea un schema `capstone_test_*` validado en la misma base, aplica el
ledger y la cadena Alembic, compara la estructura y elimina el schema en
`finally`. No crea ni elimina bases de datos.

## Tracking opcional

Los comandos científicos aceptan `--track-db`; sin la bandera, el workflow ML
continúa sin persistir el run.

```bash
cd <PROJECT_ROOT>/malaria_dl_local_project
.venv/bin/python -m src.train \
  --model custom_cnn --max-epochs 50 --track-db
.venv/bin/python -m src.evaluate \
  --checkpoint outputs/vgg16/best_model.keras --track-db
.venv/bin/python -m src.explain \
  --checkpoint outputs/vgg16/best_model.keras --method gradcam --track-db
```

Entrenamiento, evaluación, explicabilidad, SVM, ensemble y TTA registran
configuración, métricas, artefactos y errores cuando existe un run. El tracking
no debe ocultar un fallo científico: intenta registrar el error y vuelve a
propagarlo.

Las convenciones de dataset, labels, checkpoints y métricas se mantienen en
[`../docs/database_dataset_tracking.md`](../docs/database_dataset_tracking.md),
[`../docs/checkpoint_policy.md`](../docs/checkpoint_policy.md) y
[`../docs/clinical_metrics.md`](../docs/clinical_metrics.md).
