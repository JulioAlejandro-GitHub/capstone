"""Bounded reservation handshake; the HTTP process never computes attributions."""
import json
import os
import selectors
import subprocess
import sys
import threading
from typing import Any
from app.schemas.explain_generation import ExplainRequest
from src.malaria_dl.campaigns.contracts import CampaignError


class ExplainLauncher:
    # REPRESENT reuses the same handshake with its own fixed worker module.
    def __init__(self, module: str = 'app.services.explain_worker') -> None:
        self.module = module

    def launch(self, request: ExplainRequest, actor: str) -> dict[str, Any]:
        read_fd, write_fd = os.pipe()
        process = None
        try:
            process = subprocess.Popen([sys.executable, '-m', self.module],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env={**os.environ, 'CAPSTONE_EXPLAIN_RESULT_FD': str(write_fd)},
                pass_fds=(write_fd,), start_new_session=True, text=True)
            os.close(write_fd)
            write_fd = -1
            assert process.stdin is not None
            process.stdin.write(json.dumps({'request': request.model_dump(mode='json'), 'actor': actor}) + '\n')
            process.stdin.flush()
            with selectors.DefaultSelector() as selector:
                selector.register(read_fd, selectors.EVENT_READ)
                if not selector.select(timeout=60):
                    raise CampaignError('EXPLAIN_PREPARATION_TIMEOUT')
            with os.fdopen(read_fd) as stream:
                read_fd = -1
                line = stream.readline(65536)
            response = json.loads(line)
            if response.get('error'):
                raise CampaignError(response['error'])
            process.stdin.write('START\n')
            process.stdin.flush()
            process.stdin.close()
            # Reaping only; all scientific state lives in PostgreSQL.
            threading.Thread(target=process.wait, daemon=True).start()
            return response
        except BaseException:
            if process is not None:
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            raise
        finally:
            if read_fd >= 0:
                os.close(read_fd)
            if write_fd >= 0:
                os.close(write_fd)
