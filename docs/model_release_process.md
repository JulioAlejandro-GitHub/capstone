# Proceso de inventario y liberación de modelos

## Inventario y evidencia

`scripts/diagnose_model_releases.py` recorre `outputs/`, `models/`, `checkpoints/` y
`artifacts/` dentro de `malaria_dl_local_project`, además de rutas registradas en
PostgreSQL. Registra ruta absoluta y relativa, formato, SHA-256, tamaño y fecha de
modificación. La fecha es informativa y nunca resuelve linaje.

El linaje queda `resolved` sólo cuando el path contiene un UUID de un training run
conocido (`runs/<uuid>/`) o cuando una copia genérica tiene el mismo hash que los
artefactos de exactamente un training run. Cero o varios runs coincidentes dejan
`lineage_status=unresolved` y una causa en metadata. Un archivo vacío, Keras sin la
estructura ZIP requerida o HDF5 sin su firma se rechaza como corrupto/incompatible.

## Estados y promoción

`discovered` significa inventariado; `candidate`, linaje exacto y artefacto íntegro;
`validated`, evaluación reproducible y threshold referenciado; `approved`, aprobación
humana; `deployed`, activación explícita; `rejected`, corrupto/incompatible; y
`retired`, fuera de uso. Para pasar de candidate a validated se requieren evaluación,
explicabilidad, firmas de entrada/salida, preprocessing y threshold/calibración
documentados. Estos scripts no promocionan ni despliegan.

## Diagnóstico y backfill

```bash
python scripts/diagnose_model_releases.py --output-json /tmp/models.json --verbose
python scripts/diagnose_model_releases.py --strict
python scripts/backfill_model_versions.py --dry-run --output-report /tmp/backfill.json
python scripts/backfill_model_versions.py --apply --model-name custom_cnn
```

Dry-run es el valor por defecto. Apply usa una única transacción, sólo considera
training runs completados y artefactos ya registrados cuyo path, propietario y hash
coinciden, y usa restricciones/`ON CONFLICT` para ser reejecutable. No copia, cambia
ni elimina archivos; tampoco crea deployments. `--strict` falla si queda inventario
sin resolver.

## Release inmutable

```bash
python scripts/release_model_version.py \
  --training-run-id UUID --artifact-path outputs/model/runs/UUID/best_model.keras \
  --model-name model --status candidate --output-dir releases
```

El comando valida el artefacto, copia a `releases/<modelo>/<model_version_id>/`,
vuelve a comprobar SHA-256 y crea manifest, model card, snapshots, firmas y checksum.
Nunca sobrescribe un release ni modifica el origen. `--artifact-id` exige que el
registro pertenezca al training run indicado.

## Legacy y custom_cnn

`outputs/<modelo>/best_model.keras` y `final_model.keras` son aliases legacy: no son
identidad estable, el modo estricto rechaza inventarios no resueltos y frontend,
evaluación e inferencia deben referenciar `model_version_id`. En particular,
`outputs/custom_cnn/best_model.keras` sólo puede ser `candidate` si su hash coincide
con un único run; si no, permanece unresolved. Nunca se aprueba ni despliega de forma
automática y ningún threshold clínico se altera durante este proceso.
