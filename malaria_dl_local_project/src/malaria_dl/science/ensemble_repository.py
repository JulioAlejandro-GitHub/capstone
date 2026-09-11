"""E8 extends E7 append-only documents, without fictional TRAIN or new schema."""

from .ensemble import validate_configuration, validate_evaluation
from .protocol import require
from .repository import ScienceRepository


class ConfigurationRepository(ScienceRepository):
    report_event = "ml.ensemble_configuration"
    report_resource_type = "ensemble_configuration"
    report_source = "science.e8"
    report_validator = staticmethod(validate_configuration)


class EvaluationRepository(ScienceRepository):
    def read_verified(self, report_id):
        from .comparison import read_evaluation
        from .ensemble import evaluate

        result = self.read_report(report_id)
        checked = evaluate(
            result["configuration"],
            lambda eid: read_evaluation(self, eid),
            configuration_id=result["configuration_id"],
        )
        require(checked == result, "ENSEMBLE_RECONSTRUCTION_CONFLICT")
        return result

    report_event = "ml.ensemble_evaluation"
    report_resource_type = "ensemble_evaluation"
    report_source = "science.e8"
    report_validator = staticmethod(validate_evaluation)

    def persist_report(self, report):
        require(
            ConfigurationRepository(self.scope).read_report(report["configuration_id"])
            == report["configuration"],
            "ENSEMBLE_PERSISTED_CONFIGURATION_REQUIRED",
        )
        return super().persist_report(report)

    def read_report(self, report_id):
        result = super().read_report(report_id)
        require(
            ConfigurationRepository(self.scope).read_report(result["configuration_id"])
            == result["configuration"],
            "ENSEMBLE_PERSISTED_CONFIGURATION_CONFLICT",
        )
        return result


def validate_failure(value):
    require(
        value["schema"] == "ensemble_failure_e8_v1"
        and value["state"] == "failed"
        and value["reason"],
        "ENSEMBLE_FAILURE_INVALID",
    )


class FailureRepository(ScienceRepository):
    report_success = False
    report_error_code = staticmethod(lambda payload: payload["reason"])
    report_event = "ml.ensemble_failure"
    report_resource_type = "ensemble_failure"
    report_source = "science.e8"
    report_validator = staticmethod(validate_failure)


class ComparisonRepository(ScienceRepository):
    report_event = "ml.ensemble_comparison"
    report_resource_type = "ensemble_comparison"
    report_source = "science.e8"

    @staticmethod
    def report_validator(value):
        from .ensemble_reporting import validate_comparison

        validate_comparison(value)

    def persist_report(self, report):
        for item in report["items"]:
            require(
                EvaluationRepository(self.scope).read_report(item["evaluation_id"])
                == item["result"],
                "ENSEMBLE_COMPARISON_SOURCE_CONFLICT",
            )
        return super().persist_report(report)
