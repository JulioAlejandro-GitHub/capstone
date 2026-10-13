"""Reusable TFDS malaria preparation; no split/materialization or database writes."""
from __future__ import annotations

from malaria_split.source_config import CELL_SOURCE, SourceConfig, resolve_source_config
from src.malaria_dl.common.paths import get_tfds_data_dir
from src.malaria_dl.data.full_smears_download import SourceError


def prepare_cell_source(config: SourceConfig | None = None, *, verify_only: bool = False) -> dict:
    config = config or resolve_source_config()
    if config.cell_source != CELL_SOURCE:
        raise SourceError('SOURCE_MISMATCH: TFDS malaria supports the approved NLM cell_images.zip provenance; URL overrides are not passed to TFDS')
    import tensorflow_datasets as tfds

    data_dir = get_tfds_data_dir()
    dataset_path = data_dir / 'malaria/1.0.0'
    present = dataset_path.exists()
    if not present:
        if verify_only:
            raise SourceError('INTEGRITY_FAIL: TFDS malaria/1.0.0 is absent')
        # Explicit version pins the already approved builder; source URL is not an argument.
        tfds.load('malaria:1.0.0', split='train', as_supervised=True, with_info=True,
                  data_dir=str(data_dir), try_gcs=False)
    # Never download, repair or overwrite an existing prepared cache during verification.
    builder = tfds.builder_from_directory(str(dataset_path))
    info = builder.info
    if str(info.version) != '1.0.0' or info.features['label'].names != ['parasitized', 'uninfected']:
        raise SourceError('SOURCE_MISMATCH: unexpected TFDS version or labels')
    counts = [0, 0]
    dataset = builder.as_dataset(split='train', as_supervised=True, shuffle_files=False)
    for image, label in tfds.as_numpy(dataset):
        label = int(label)
        if image.ndim != 3 or image.shape[2] != 3 or label not in (0, 1):
            raise SourceError('INTEGRITY_FAIL: invalid TFDS example')
        counts[label] += 1
    if counts != [13779, 13779] or info.splits['train'].num_examples != 27558:
        raise SourceError('INTEGRITY_FAIL: incomplete TFDS malaria distribution')
    return {'dataset': 'NLM-Falciparum-Thin-Cell-Images', 'source': config.cell_source,
            'destination': str(dataset_path), 'mechanism': 'TFDS malaria 1.0.0',
            'source_evidence': 'approved S1.1 provenance; arbitrary SOURCE overrides rejected',
            'integrity': 'PASS', 'status': 'ALREADY_DOWNLOADED' if present else 'READY',
            'download_performed': not present, 'images': sum(counts),
            'class_counts': dict(zip(info.features['label'].names, counts))}
