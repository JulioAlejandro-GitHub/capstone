"""Technical Stage 2 eligibility, independent of metrics and deployment readiness."""

from typing import Any


def evaluation_completed(context: dict[str, Any]) -> bool:
    if not context.get("evaluation_link_valid", True):
        return False
    if context.get("evaluation_source_kind", "run") == "assessment_e6":
        return bool(
            context.get("evaluation_attempt_id")
            and context.get("evaluation_identity_id")
            and context.get("evaluation_status") == "verified"
            and context.get("evaluation_finished_at")
            and context.get("evaluation_verified_evidence")
            and context.get("evaluation_link_valid") is True
        )
    return bool(context.get("evaluation_run_id") and context.get("evaluation_status") == "completed")


def stage2_eligibility(context: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    train_completed = context.get("run_type", "training") == "training" and context.get("train_status") == "completed"
    completed = evaluation_completed(context)
    missing = []
    if not train_completed:
        missing.append("TRAIN no completado")
    if not (context.get("evaluation_run_id") or context.get("evaluation_attempt_id")):
        missing.append("EVALUATE no encontrado")
    elif not completed:
        missing.append("EVALUATE no completado")
    return train_completed and completed, {
        "train_completed": train_completed, "evaluate_completed": completed,
        "missing_conditions": missing,
    }
