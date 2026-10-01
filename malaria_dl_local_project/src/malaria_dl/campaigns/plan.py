"""campaign_id -> execution plan. READ ONLY; stops at the execution boundary, never claims.

The plan is rebuilt only from the frozen PostgreSQL contract (``CampaignRepository.get`` already
revalidates contract/configuration hashes and the materialized members); current defaults are
never consulted. ``execution_readiness`` reports, without side effects, the same conditions the
executor (``execution.campaign.preflight`` / ``claim``) will require, so a plan can be certified
without reserving an attempt, writing dataset evidence or starting TRAIN.
"""

from .contracts import CampaignError
from .repository import execute, identifier

ENTRY_POINT = "run_train_all_models.py"
EXECUTION_BOUNDARY = "execution.campaign.execute_campaign -> ExecutionRepository.claim -> worker -> TRAIN"


def execution_command(campaign_id):
    return f"python {ENTRY_POINT} --campaign-id {identifier(campaign_id)}"


def resolve_plan(row):
    """Pure: validated repository row -> ordered experiments with their frozen configuration."""
    if row["state"] == "draft":
        raise CampaignError("CAMPAIGN_NOT_FROZEN")
    contract = row["contract"]
    matrix = contract["matrix"]
    configurations = {}
    for h, item in matrix["configurations"].items():
        resolved = item["configuration"]["resolved"]
        configurations[h] = dict(
            configuration_hash=h,
            model_id=item["configuration"]["model_id"],
            adapter_version=item["configuration"]["adapter_version"],
            optimizer=resolved["optimizer"]["name"],
            variants=sorted(r["variant"] for r in item["requests"]),
            model=resolved["model"],
            optimizer_parameters=resolved["optimizer"]["parameters"],
            fine_tune_learning_rate=resolved["optimizer"]["fine_tune_learning_rate"],
            execution=resolved["execution"],
        )
    experiments = []
    for member in row["members"]:
        config = configurations[member["configuration_hash"]]
        experiments.append(dict(
            position=member["position"], member_id=str(member["id"]), state=member["state"],
            model_id=config["model_id"], optimizer=config["optimizer"], seed=member["seed"],
            variants=config["variants"], configuration_hash=member["configuration_hash"],
            excluded=member["exclusion_reason"] is not None,
        ))
    models = sorted({c["model_id"] for c in configurations.values()})
    return dict(
        campaign_id=str(row["id"]),
        name=row["name"],
        purpose=row["purpose"],
        state=row["state"],
        contract_hash=row["contract_hash"],
        frozen_at=row["frozen_at"],
        dataset_version_id=str(row["dataset_version_id"]),
        dataset=dict(counts=row["dataset_snapshot"].get("counts"),
                     dataset_materialization_id=row["dataset_snapshot"].get("dataset_materialization_id"),
                     dataset_evidence_id=str(row["dataset_evidence_id"])),
        models=models,
        optimizers=sorted({c["optimizer"] for c in configurations.values()}),
        seeds=matrix["seeds"],
        protocol=dict(version=contract["protocol"]["version"],
                      early_stopping=contract["protocol"]["early_stopping"],
                      checkpoint=contract["protocol"]["checkpoint"],
                      sensitivity_target=contract["protocol"]["sensitivity_target"],
                      budget=contract["protocol"]["budget"],
                      test_access=contract["protocol"]["test_access"]),
        configurations=sorted(configurations.values(),
                              key=lambda c: (c["model_id"], c["optimizer"], c["variants"], c["configuration_hash"])),
        experiments=experiments,
        total_experiments=len(experiments),
        expected_count=row["expected_count"],
        experiments_per_model={m: sum(e["model_id"] == m for e in experiments) for m in models},
        command=execution_command(row["id"]),
        execution_boundary=EXECUTION_BOUNDARY,
    )


def _check(checks, name, ok, code=None, **detail):
    checks.append(dict(check=name, status="PASS" if ok else "FAIL", code=None if ok else code, **detail))


def execution_readiness(repository, row, *, environment=None, dataset_resolver=None):
    """Side-effect free view of the executor's preconditions in THIS process environment."""
    from ..data.governed_dataset import assert_run_dataset_snapshot_unchanged, resolve_governed_dataset
    from ..execution.campaign import IDENTITY_KEYS
    from ..models.registry import resolve_descriptor
    from .service import planning_environment

    checks = []
    _check(checks, "campaign_state_executable", row["state"] in ("frozen", "active"),
           "USE_RESUME_FOR_STARTED_CAMPAIGN" if row["state"] == "paused" else "CAMPAIGN_NOT_EXECUTABLE",
           state=row["state"])
    try:
        repository.preflight_e10_schema()
        _check(checks, "e10_schema", True)
    except Exception as exc:  # noqa: BLE001 -- reported, never raised: plan stays readable
        _check(checks, "e10_schema", False, type(exc).__name__)
    current = (environment or planning_environment)()
    differing = sorted(k for k in IDENTITY_KEYS if current.get(k) != row["environment"].get(k))
    _check(checks, "code_environment_identity", not differing,
           "FROZEN_CODE_ENVIRONMENT_CONFLICT_NEW_CAMPAIGN_REQUIRED", differing_keys=differing)
    adapters_ok, test_ok = True, True
    for item in row["contract"]["matrix"]["configurations"].values():
        config = item["configuration"]
        frozen = next(d for d in row["contract"]["matrix"]["registry"] if d["id"] == config["model_id"])
        try:
            d = resolve_descriptor(config["model_id"])
            adapters_ok &= d.version == config["adapter_version"] and d.adapter == frozen["adapter"]
        except ValueError:
            adapters_ok = False
        test_ok &= config["resolved"]["execution"]["evaluate_best_on_test"] is False
    _check(checks, "frozen_adapters_available", adapters_ok, "FROZEN_ADAPTER_CONFLICT")
    _check(checks, "test_forbidden", test_ok, "TEST_FORBIDDEN")
    try:
        snapshot = (dataset_resolver or resolve_governed_dataset)(str(row["dataset_version_id"]))
        assert_run_dataset_snapshot_unchanged(snapshot, row["dataset_snapshot"])
        _check(checks, "dataset_snapshot_unchanged", True)
    except Exception as exc:  # noqa: BLE001 -- governed dataset errors carry public codes only
        _check(checks, "dataset_snapshot_unchanged", False, str(exc) or type(exc).__name__)
    models = sorted({i["configuration"]["model_id"] for i in row["contract"]["matrix"]["configurations"].values()})
    with repository.transaction(readonly=True) as c:
        counts = {m: execute(c, "SELECT count(*) FROM models WHERE name=:name", name=m).scalar_one()
                  for m in models}
    _check(checks, "model_catalog_identity", all(n == 1 for n in counts.values()),
           "CANONICAL_MODEL_CATALOG_IDENTITY_REQUIRED", rows_per_model=counts)
    return dict(ready=all(c["status"] == "PASS" for c in checks), checks=checks,
                note="Read-only diagnosis; no attempt reserved, no dataset evidence written, TRAIN not started.")
