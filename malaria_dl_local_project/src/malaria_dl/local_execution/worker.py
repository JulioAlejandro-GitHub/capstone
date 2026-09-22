"""One local TRAIN, reads only an assigned job and API reporting credentials."""
import json,sys,os
from pathlib import Path
from .transport import Api,Reports
from .storage import resolve,verify_samples


def main():
    # Parent sends the assignment only after heartbeat accepted its PID identity.
    message=json.load(sys.stdin);job=message['job'];roots=message['roots']
    api=Api(message['url'],os.environ['CAPSTONE_AGENT_BEARER'])
    session=job['session'];dataset_root=roots[session['dataset']['dataset_root']['root_id']]
    verify_samples(dataset_root,job['dataset_manifest'])
    artifact_root=roots[job['artifact_root_id']]
    session['dataset']['dataset_root']=str(Path(dataset_root).resolve(strict=True))
    session['artifact_root']=str(resolve(artifact_root,session['artifact_root']['relative_path']))
    from ..execution.train import train
    from ..models.registry import resolve_descriptor
    from .event_runtime import compose
    from ..execution.contracts import RunEventType
    from ..execution.journal import JournalError
    journal, emitter = compose(api, job, message['event_journal'], artifact_root)
    with journal:
        if not journal.created:
            if emitter.pending is not None:
                emitter.retry_pending()
            # Transport recovery is safe; restarting epochs/checkpoints is not.
            raise JournalError('LOCAL_SCIENTIFIC_RESUME_UNSUPPORTED')
        try:
            train(Reports(api,job,artifact_root),session,
                  resolve_descriptor(session['configuration']['model_id']), event_emitter=emitter)
        except BaseException as original:
            if emitter.pending is None and not emitter.closed:
                try:
                    emitter.emit(RunEventType.TRAINING_FAILED, {'cause':'TRAIN_RUNTIME_FAILED'})
                except BaseException:
                    original.add_note('E10_FAILURE_EVENT_UNCONFIRMED')
            raise

if __name__=='__main__':main()
