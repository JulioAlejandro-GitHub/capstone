"""Campaign assessments of evaluation-only (zero-shot) models: no database, no runtime."""
import json
from argparse import Namespace

import pytest

from src.malaria_dl.assessment import cli

ZERO = {"id": "31d27b2d-6e90-4530-a589-ae92c91281df", "status": "completed", "campaign_id": "c",
        "model_name": "biomedclip_zero_shot", "evaluation_only": True,
        "campaign_dataset_version_id": "d", "campaign_seed": 11, "campaign_batch_size": 32}
KERAS = {"id": "910051e5-a00c-44c4-9d23-77598af470f7", "status": "completed", "campaign_id": "c",
         "model_name": "vgg16"}


def args(kind="evaluate", **changes):
    value = cli.parser(kind).parse_args(["--campaign-id", "2634e758-5c5c-4c6b-a4db-7fcbc37be082"])
    return Namespace(**{**vars(value), **changes})


@pytest.fixture
def prepared(monkeypatch):
    calls = []

    def prepare(repository, **kw):
        calls.append(kw)
        return {}

    monkeypatch.setattr(cli, "prepare", prepare)
    monkeypatch.setattr(cli, "run", lambda *a: {"id": "a", "state": "verified", "verification": {}})
    return calls


def test_evaluation_only_item_takes_the_campaign_dataset_seed_and_batch(prepared):
    assert cli._assess("evaluate", args(), ZERO, None)["state"] == "verified"
    assert (prepared[0]["dataset_version_id"], prepared[0]["seed"], prepared[0]["batch_size"]) == ("d", 11, 32)
    cli._assess("test", args("test", seed=7, batch_size=8, dataset_version_id="x"), ZERO, None)
    assert (prepared[1]["dataset_version_id"], prepared[1]["seed"], prepared[1]["batch_size"]) == ("x", 7, 8)
    cli._assess("evaluate", args(), KERAS, None)  # trained members keep their TRAIN profile
    assert (prepared[2]["dataset_version_id"], prepared[2]["seed"], prepared[2]["batch_size"]) == (None, "auto", None)


def test_campaign_gradcam_skips_vit_models_without_failing(monkeypatch, prepared, capsys):
    monkeypatch.setattr(cli, "AssessmentRepository", lambda: None)
    monkeypatch.setattr(cli, "select_trainings", lambda *a: [KERAS, ZERO])
    monkeypatch.setattr(cli, "item_python", lambda item: None)
    assert cli._execute("explain", args("explain")) == 0
    output = json.loads(capsys.readouterr().out)
    assert output[0]["state"] == "verified"
    assert output[1] == {"source_training_run_id": ZERO["id"], "state": "skipped", "reason": "GRADCAM_NOT_APPLICABLE_VIT"}
    assert len(prepared) == 1


def test_items_of_another_framework_run_in_their_environment(monkeypatch, capsys):
    from src.malaria_dl.execution import process_verification

    seen = []

    def owned(python, code, argv, phase):
        seen.append((python, argv[0], json.loads(argv[2])["id"], phase))
        with open(argv[3], "w") as stream:
            json.dump({"attempt_id": "b", "state": "verified", "verification": {}}, stream)
        return 0

    monkeypatch.setattr(process_verification, "owned_process", owned)
    monkeypatch.setattr(cli, "AssessmentRepository", lambda: None)
    monkeypatch.setattr(cli, "select_trainings", lambda *a: [ZERO])
    monkeypatch.setattr(cli, "item_python", lambda item: "/venv-torch/python")
    assert cli._execute("evaluate", args()) == 0
    assert seen == [("/venv-torch/python", "evaluate", ZERO["id"], "ASSESSMENT")]
    assert json.loads(capsys.readouterr().out)[0]["attempt_id"] == "b"


def test_a_failed_delegated_process_is_a_failed_item(monkeypatch):
    from src.malaria_dl.execution import process_verification

    monkeypatch.setattr(process_verification, "owned_process", lambda *a: 3)
    assert cli._delegate("evaluate", args(), ZERO, "/p") == {"state": "failed", "error": "ASSESSMENT_PROCESS_FAILED"}
