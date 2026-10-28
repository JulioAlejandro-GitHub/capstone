"""Load a checkpoint in an owned disposable process, never in the coordinator."""
import json
import os
import subprocess
import sys
from .global_gate import CURRENT
from ..campaigns.contracts import CampaignError


def isolated_checkpoint_loader(path, contract):
    """The checkpoint loads in the environment of its framework (.venv-metal or .venv-torch locally)."""
    gate = CURRENT.get()
    if gate is None:
        raise CampaignError('GLOBAL_EXECUTION_OWNER_REQUIRED')
    gate.require_healthy()
    read_fd, write_fd = os.pipe()
    process = None
    try:
        from .artifacts import checkpoint_framework
        from .local_launch import framework_python

        process = subprocess.Popen(
            [framework_python(checkpoint_framework(contract)), '-B', '-c',
             'import sys,json; from src.malaria_dl.execution.global_gate import attach_worker; '
             'attach_worker(); from src.malaria_dl.execution.artifacts import checkpoint_loader; '
             'checkpoint_loader(sys.argv[1],json.loads(sys.argv[2]))', str(path), json.dumps(contract)],
            start_new_session=True, pass_fds=(read_fd,),
            env={**os.environ, 'CAPSTONE_EXECUTION_TOKEN': gate.owner,
                 'CAPSTONE_START_FD': str(read_fd)},
        )
        gate.child_started(process.pid)
        os.write(write_fd, b'1')
        code = process.wait()
        gate.after_wait(process.pid, code, 'CHECKPOINT_LOAD')
        gate.require_healthy()
        if code != 0:
            raise CampaignError('CHECKPOINT_LOAD_PROCESS_FAILED')
    finally:
        os.close(read_fd)
        os.close(write_fd)
        # Unfinished verification retains the durable process fence; never authorize
        # another experiment on the basis of a closed database connection alone.


isolated_keras_loader = isolated_checkpoint_loader  # historical name
