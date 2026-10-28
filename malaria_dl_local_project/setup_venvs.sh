#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3.12}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: Python 3.12 no encontrado. Instálalo o define PYTHON_BIN." >&2
  exit 1
fi

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "ERROR: Este instalador está diseñado para macOS Apple Silicon (arm64)." >&2
  exit 1
fi

install_env() {
  local target="$1" requirements="$2"
  if [[ -e "$target" ]]; then
    echo "ERROR: $target ya existe; no se modificó. Renómbralo o elimínalo manualmente si quieres recrearlo." >&2
    return 1
  fi
  "$PYTHON_BIN" -m venv "$target"
  "$target/bin/python" -m pip install --upgrade pip
  "$target/bin/python" -m pip install -r "$requirements"
  "$target/bin/python" -m pip check
  if [[ "$target" == .venv-torch ]]; then
    "$target/bin/python" -c 'import torch, open_clip; print("PyTorch:", torch.__version__, "OpenCLIP:", open_clip.__version__); print("MPS:", torch.backends.mps.is_available())'
  else
    "$target/bin/python" -c 'import tensorflow as tf; print("TensorFlow:", tf.__version__); print("GPU:", tf.config.list_physical_devices("GPU"))'
  fi
}

case "${1:-}" in
  cpu) install_env .venv-local-train requirements-cpu.txt ;;
  gpu) install_env .venv-metal requirements-gpu.txt ;;
  torch) install_env .venv-torch requirements-torch.txt ;;
  all)
    install_env .venv-local-train requirements-cpu.txt
    install_env .venv-metal requirements-gpu.txt
    ;;
  *) echo "Uso: $0 {cpu|gpu|torch|all}" >&2; exit 2 ;;
esac
