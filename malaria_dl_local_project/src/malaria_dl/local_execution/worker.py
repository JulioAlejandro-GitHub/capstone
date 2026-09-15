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
    train(Reports(api,job,artifact_root),session,resolve_descriptor(session['configuration']['model_id']))

if __name__=='__main__':main()
