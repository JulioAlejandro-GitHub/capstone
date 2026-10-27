"""Pretrained catalog visibility and computational TRAIN omission."""
from uuid import uuid4

from src.malaria_dl.models import registry
from src.malaria_dl.persistence import run_repository

ARCHITECTURE = "biomedclip_zero_shot"
DATASET = "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2"


def test_pretrained_uses_common_model_catalog(monkeypatch):
    writes = []
    monkeypatch.setattr(run_repository, "_query_one", lambda *a: None)
    monkeypatch.setattr(run_repository, "_execute_returning_id",
                        lambda sql, params: writes.append((sql, params)) or "model-id")
    assert run_repository.get_or_create_model(
        ARCHITECTURE, "classification", framework="pytorch/open_clip",
        architecture=ARCHITECTURE, pretrained=True,
        metadata={"trainable": False},
    ) == "model-id"
    assert "INSERT INTO models" in writes[0][0]
    assert writes[0][1]["pretrained"] is True
    monkeypatch.setattr(registry, "model_catalog", lambda: (
        {"name": ARCHITECTURE, "architecture": ARCHITECTURE,
         "model_type": "classification", "framework": "pytorch/open_clip"},
    ))
    assert registry.registered_models() == (ARCHITECTURE,)
    assert registry.MODEL_REGISTRY[ARCHITECTURE].trainable is False


def test_train_skips_and_continues_without_registration(monkeypatch, capsys):
    from src.malaria_dl.execution import operations
    base = dict(id=str(uuid4()), dataset_version_id=DATASET, campaign_id=None)
    zero = dict(base, model_name=ARCHITECTURE, configuration=None)
    config = {'model_id':'custom_cnn','schema_version':'test','adapter_version':'test',
              'resolved':dict.fromkeys(('model','optimizer','execution','selection','input_contract','recipe'), {})}
    trained = dict(base, id=str(uuid4()), model_name='custom_cnn', configuration=config)
    monkeypatch.setattr(operations, 'select_trainings', lambda *a: [zero,trained])
    plan = operations.training_plan(object(), None, base['id'])
    assert len(plan) == 1 and plan[0]['source_training_run_id'] == trained['id']
    assert 'No requiere entrenamiento local' in capsys.readouterr().out
    monkeypatch.setattr(operations, 'select_trainings', lambda *a: [zero])
    assert operations.training_plan(object(), None, base['id']) == []
    from src.malaria_dl.execution.train import standalone
    from types import SimpleNamespace
    assert standalone(SimpleNamespace(model=ARCHITECTURE)) == {'state':'omitted'}


def test_train_main_continues_trainable_sources(monkeypatch, capsys):
    from src.malaria_dl.execution import operations, local_launch, train
    source = str(uuid4())
    config = {'model_id':'custom_cnn','schema_version':'test','adapter_version':'test',
              'resolved':dict.fromkeys(('model','optimizer','execution','selection','input_contract','recipe'), {})}
    rows = [dict(id=str(uuid4()),model_name=ARCHITECTURE,configuration=None),
            dict(id=source,model_name='custom_cnn',configuration=config,campaign_id=None,dataset_version_id=DATASET)]
    monkeypatch.setattr(local_launch,'bootstrap',lambda:None)
    monkeypatch.setattr(operations,'select_trainings',lambda *a:rows)
    called=[]
    def execute_train(args):
        called.append(args.model)
        return {'run_id':str(uuid4()),'state':'verified'}
    monkeypatch.setattr(train,'standalone',execute_train)
    assert operations.main(['--source-training-run-id',source]) == 0
    assert called == ['custom_cnn'] and 'No requiere entrenamiento local' in capsys.readouterr().out
