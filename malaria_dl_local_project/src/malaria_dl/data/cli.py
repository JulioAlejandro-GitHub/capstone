from src.config import PHYSICAL_DATASET_DIR

DATA_SOURCE_CHOICES = ["physical", "tfds"]
DATA_SOURCE_PHYSICAL = "physical"


def add_data_source_args(parser, *, governed=False):
    parser.add_argument(
        "--data-source",
        "--dataset-source",
        choices=DATA_SOURCE_CHOICES,
        default=DATA_SOURCE_PHYSICAL,
        help=(
            "Fuente de datos. Default oficial: physical. "
            "Usa tfds solo como fallback explícito/legacy."
        ),
    )
    parser.add_argument(
        "--dataset-dir",
        default=None
        if governed
        else str(PHYSICAL_DATASET_DIR.relative_to(PHYSICAL_DATASET_DIR.parents[1])),
        help=(
            "Comprobación opcional: debe coincidir con la raíz gobernada heredada."
            if governed
            else "Ruta del split físico. Default: data/malaria_physical_split."
        ),
    )
    return parser
