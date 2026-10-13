"""EXEC.1 selection from PostgreSQL, shared by all public entrypoints."""
from typing import Any

from ..campaigns.repository import CampaignRepository, execute, identifier
from ..assessment.contracts import require


def select_trainings(repository: CampaignRepository, campaign_id: str | None,
                     training_run_id: str | None) -> list[dict[str, Any]]:
    require(bool(campaign_id or training_run_id), "CAMPAIGN_OR_SOURCE_TRAINING_RUN_REQUIRED")
    campaign = identifier(campaign_id) if campaign_id else None
    training = identifier(training_run_id) if training_run_id else None
    with repository.transaction(readonly=True) as c:
        if campaign:
            require(execute(c, "SELECT EXISTS(SELECT 1 FROM experimental_campaigns WHERE id=CAST(:id AS uuid))",
                            id=campaign).scalar_one(), "CAMPAIGN_NOT_FOUND")
        rows = list(execute(c, """
            SELECT r.id, r.campaign_id, r.dataset_version_id, r.status,
                   r.execution_parameters->'model_configuration_e2'->'configuration' AS configuration
            FROM runs r WHERE r.run_type='training'
              AND (CAST(:train AS uuid) IS NULL OR r.id=CAST(:train AS uuid))
              AND (CAST(:train AS uuid) IS NOT NULL OR r.campaign_id=CAST(:campaign AS uuid)
                   OR EXISTS(SELECT 1 FROM campaign_attempts a JOIN campaign_members m ON m.id=a.member_id
                             WHERE a.training_run_id=r.id AND m.campaign_id=CAST(:campaign AS uuid)))
            ORDER BY r.started_at,r.id
        """, train=training, campaign=campaign).mappings())
        require(bool(rows), "SOURCE_TRAINING_RUN_NOT_FOUND" if training else "CAMPAIGN_HAS_NO_TRAININGS")
        if campaign and training:
            belongs = str(rows[0]["campaign_id"]) == campaign or execute(c, """
                SELECT EXISTS(SELECT 1 FROM campaign_attempts a JOIN campaign_members m ON m.id=a.member_id
                    WHERE a.training_run_id=CAST(:train AS uuid) AND m.campaign_id=CAST(:campaign AS uuid))
            """, train=training, campaign=campaign).scalar_one()
            require(belongs, "SOURCE_TRAINING_RUN_CAMPAIGN_MISMATCH")
    return [dict(row) for row in rows]
