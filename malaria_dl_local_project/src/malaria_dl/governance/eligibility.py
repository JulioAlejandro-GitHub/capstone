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


ZERO_SHOT_CONTRACT = "openclip_input_v1"
ZERO_SHOT_CALIBRATION = "zero_shot_val_calibration_v1"


def is_zero_shot(evaluation: dict[str, Any]) -> bool:
    binding = evaluation.get("model_binding") or {}
    return (binding.get("input_contract") or {}).get("schema_version") == ZERO_SHOT_CONTRACT


def select_evaluation(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The evaluation whose decision a cell activation uses; candidates are newest first.

    A zero-shot model prefers its VAL-calibrated EVALUATE: the newest completed one may be a
    TEST at the uncalibrated argmax threshold. Other models keep the newest completed one.
    """
    completed = [item for item in candidates if evaluation_completed(item)]
    calibrated = [item for item in completed if is_zero_shot(item)
                  and item.get("evaluation_split") == "val"
                  and item.get("evaluation_decision_source") == ZERO_SHOT_CALIBRATION]
    return (calibrated or completed or [None])[0]


def stage2_eligibility(context: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    train_completed = context.get("run_type", "training") == "training" and context.get("train_status") == "completed"
    completed = evaluation_completed(context)
    missing = []
    if context.get("run_type", "training") != "training":
        missing.append("El origen no es un TRAIN")
    return not missing, {
        "train_completed": train_completed, "evaluate_completed": completed,
        "missing_conditions": missing,
    }
