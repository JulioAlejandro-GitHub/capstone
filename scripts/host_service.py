"""launchd entrypoint for the macOS host services (installed by scripts/host_services.sh).

Run by the `.venv-metal` interpreter, never by a shell script: the repository lives in ~/Desktop, which
macOS protects, and only that interpreter is granted Full Disk Access. Stdlib only before exec.

  yolo     cl.capstone.yolo-detector  runtime_yolo.py on 127.0.0.1:8765, only if CELL_DETECTOR_KEY=yolo26_seg_v1
  explain  cl.capstone.explain-agent  app.services.explain_agent (EXPLAIN from the report on the GPU)

Exit code 0 means "not applicable" (launchd does not restart it); any other code is restarted.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YOLO_DETECTOR = 'yolo26_seg_v1'


def read_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def permission_hint(error: OSError) -> int:
    print(f'HOST_SERVICE_PERMISSION_DENIED: {type(error).__name__}: {error.strerror}\n'
          f'Concede "Acceso total al disco" a {os.path.realpath(sys.executable)} '
          '(Ajustes del Sistema → Privacidad y seguridad) y ejecuta scripts/host_services.sh restart.',
          file=sys.stderr, flush=True)
    return 78  # EX_CONFIG


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ('yolo', 'explain'):
        print('uso: host_service.py yolo|explain', file=sys.stderr)
        return 64
    try:
        env = read_env(ROOT / '.env')
    except OSError as error:
        return permission_hint(error)
    if argv[1] == 'yolo':
        if env.get('CELL_DETECTOR_KEY') != YOLO_DETECTOR:
            print(f'yolo-detector no aplica: CELL_DETECTOR_KEY={env.get("CELL_DETECTOR_KEY")!r}', flush=True)
            return 0
        os.environ.update({key: value for key, value in env.items() if key.startswith('YOLO_')})
        os.chdir(ROOT)
        os.execv(sys.executable, [sys.executable, 'smear_segmentation_project/runtime_yolo.py',
                                  '--host', '127.0.0.1', '--port', '8765'])
    os.chdir(ROOT / 'backend_api')
    os.environ['PYTHONPATH'] = os.pathsep.join(str(path) for path in (
        ROOT / 'backend_api', ROOT / 'malaria_dl_local_project', ROOT / 'malaria_dataset_split_project' / 'src'))
    os.execv(sys.executable, [sys.executable, '-m', 'app.services.explain_agent'])
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
