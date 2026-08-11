# Malaria Dataset Split Project

## Propósito

Construir y gobernar datasets experimentales reproducibles para el proyecto de malaria.

## Responsabilidades futuras

- descubrimiento de fuentes;
- identidad clínica;
- versionado de datasets;
- partición agrupada por paciente;
- balance y validaciones anti-leakage;
- persistencia científica;
- materialización física, reconciliación y reportabilidad.

## Alcance de SPLIT 1A

Esta etapa contiene únicamente una auditoría reproducible y de solo lectura del split
físico histórico. PostgreSQL será el *source of truth* científico; el filesystem será
su materialización y CSV/JSON serán derivados. El dataset original y toda versión
`FROZEN` se tratarán como inmutables. Estos principios se documentan aquí, pero todavía
no se implementan.

## Fuera de alcance

TRAIN, evaluación del modelo, inferencia, producción, Grad-CAM y YOLO. Tampoco se crea
un split nuevo ni se investiga Patient-ID en esta etapa.

`malaria_dataset_split_project` prepara, versiona, valida y materializa datasets;
`malaria_dl_local_project` entrena y evalúa modelos.

## Uso

```bash
python -m malaria_split.cli audit-current-split
```

El comando toma por defecto `config/current_split.yaml` y sólo inspecciona archivos.

Los tests no requieren dependencias externas:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'
```

La auditoría de identidad requiere Pillow para calcular hashes de píxeles decodificados.

SPLIT 1B agrega una auditoría de identidad clínica:

```bash
PYTHONPATH=src python -m malaria_split.cli audit-patient-identity
```

Los dos CSV oficiales NLM indicados en `config/current_split.yaml` se mantienen como
copias regenerables bajo `var/audit/source/`; tanto ellos como el JSON detallado son
artefactos locales ignorados por Git. No son la persistencia científica definitiva.

SPLIT 1C incorpora introspección PostgreSQL explícitamente read-only:

```bash
PYTHONPATH=src ../malaria_dl_local_project/.venv/bin/python \
  -m malaria_split.cli audit-system-contracts
```
