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
                   r.execution_parameters->'scientific_origin' AS scientific_origin,
                   (SELECT name FROM models WHERE id=r.model_id) AS model_name,
                   (SELECT metadata FROM models WHERE id=r.model_id) AS model_metadata,
                   r.execution_parameters->'model_configuration_e2'->'configuration' AS configuration
            FROM runs r WHERE r.run_type='training'
              AND (CAST(:train AS uuid) IS NULL OR r.id=CAST(:train AS uuid))
              AND (CAST(:campaign AS uuid) IS NULL OR r.campaign_id=CAST(:campaign AS uuid)
                   OR EXISTS(SELECT 1 FROM campaign_attempts a JOIN campaign_members m ON m.id=a.member_id
                             WHERE a.training_run_id=r.id AND m.campaign_id=CAST(:campaign AS uuid)))
            ORDER BY r.started_at,r.id
        """, train=training, campaign=campaign).mappings())
        rows = [dict(row) for row in rows]
        if campaign:
            rows += evaluation_only_trainings(c, campaign, training)
        require(bool(rows), "SOURCE_TRAINING_RUN_CAMPAIGN_SELECTION_EMPTY" if campaign and training
                else "SOURCE_TRAINING_RUN_NOT_FOUND" if training else "CAMPAIGN_HAS_NO_TRAININGS")
    return rows


def evaluation_only_trainings(c, campaign: str, training: str | None) -> list[dict[str, Any]]:
    """Registered logical TRAIN of each campaign evaluation-only model (zero-shot).

    They have no campaign member: TRAIN skips them, and the campaign supplies what an
    explicit run would require (its dataset, its smallest seed, the model's versioned batch).
    """
    from ..models.registry import evaluation_only, resolve_descriptor

    rows = [dict(row) for row in execute(c, """
        SELECT r.id, CAST(:campaign AS uuid) AS campaign_id, r.dataset_version_id, r.status,
               r.execution_parameters->'scientific_origin' AS scientific_origin,
               m.name AS model_name, m.metadata AS model_metadata, NULL::jsonb AS configuration,
               e.dataset_version_id AS campaign_dataset_version_id,
               (SELECT min(CAST(s AS integer)) FROM jsonb_array_elements_text(e.requested->'seeds') s) AS campaign_seed
        FROM experimental_campaigns e
        CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(e.requested->'evaluation_models','[]'::jsonb)) wanted(name)
        JOIN models m ON m.name=wanted.name AND m.metadata->>'training_mode'='logical'
        JOIN runs r ON r.model_id=m.id AND r.run_type='training'
        WHERE e.id=CAST(:campaign AS uuid) AND (CAST(:train AS uuid) IS NULL OR r.id=CAST(:train AS uuid))
        ORDER BY m.name,r.started_at,r.id
    """, campaign=campaign, train=training).mappings()]
    names = [row["model_name"] for row in rows]
    require(len(names) == len(set(names)), "LOGICAL_TRAIN_NOT_UNIQUE")
    for row in rows:
        row["evaluation_only"] = True
        row["campaign_batch_size"] = evaluation_only(
            resolve_descriptor(row["model_name"], executable=False))["assessment_batch_size"]
    return rows
