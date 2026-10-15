from typing import Annotated, Any
from fastapi import Depends
from app.config import Settings, get_settings
from app.repositories.catalog import CatalogRepository
from app.services.scientific_public import public_evidence


class CatalogService:
    def __init__(self, repository: CatalogRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def models(self, datasource: str | None, traceability: bool = False) -> dict[str, Any]:
        items = self.repository.models(datasource)
        if traceability:
            items = [public_evidence({key: value for key, value in item.items()
                                      if not key.startswith('best_')})
                     for item in items if item['model_type'] == 'classification']
        for item in items:
            item['training_evidence_status'] = 'available' if item['training_runs'] else 'not_generated'
            item['has_training_runs'] = bool(item['training_runs'])
            item['has_completed_training'] = any(r['status'] == 'completed' for r in item['training_runs'])
        return {'items': items, 'comparison': {
            'scc_max_comparison_runs': self.settings.scc_max_comparison_runs,
        }}


def get_catalog_service(
    repository: Annotated[CatalogRepository, Depends()],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CatalogService:
    return CatalogService(repository, settings)
