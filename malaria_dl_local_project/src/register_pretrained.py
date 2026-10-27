"""Explicit registration of a frozen BiomedCLIP origin; never executes TRAIN."""
import argparse
import json
from pathlib import Path


def main(argv=None):
    from src.malaria_dl.data.governed_dataset import dataset_uuid_arg
    from src.malaria_dl.pretrained.service import register_pretrained

    parser = argparse.ArgumentParser(allow_abbrev=False, description=__doc__)
    parser.add_argument("--dataset-version-id", required=True, type=dataset_uuid_arg)
    parser.add_argument("--biomedclip-directory", required=True, type=Path)
    parser.add_argument("--text-directory", required=True, type=Path)
    parser.add_argument("--database-url-env", help="Variable de entorno con una conexión PostgreSQL explícita (p. ej. base aislada)")
    args = parser.parse_args(argv)
    try:
        options = {}
        if args.database_url_env:
            import os
            from sqlalchemy import create_engine
            from sqlalchemy.engine import make_url
            from src.malaria_dl.pretrained.contracts import require
            url = make_url(os.environ[args.database_url_env])
            require(url.drivername in ("postgresql", "postgresql+psycopg") and bool(url.host) and bool(url.database),
                    "PRETRAINED_DATABASE_URL_INVALID")
            url = url.set(drivername="postgresql+psycopg")
            options["engine_factory"] = lambda: create_engine(url, pool_pre_ping=True)
        result = register_pretrained(dataset_version_id=args.dataset_version_id,
                                     biomedclip_directory=args.biomedclip_directory, text_directory=args.text_directory, **options)
    except Exception as exc:
        from src.malaria_dl.campaigns.contracts import CampaignError
        from src.malaria_dl.data.governed_dataset import GovernedDatasetError
        # Never print SQLAlchemy parameters or database credentials on error.
        print(json.dumps({"state": "failed", "error": str(exc) if isinstance(exc, (CampaignError, GovernedDatasetError))
                          else "PRETRAINED_REGISTRATION_FAILED", "exception_class": type(exc).__name__}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
