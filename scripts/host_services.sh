#!/usr/bin/env bash
# macOS host services as launchd user agents (they start at login and restart on failure).
#
#   scripts/host_services.sh install|start|status|restart|stop|uninstall|logs [yolo|explain]
#
#   yolo     cl.capstone.yolo-detector   YOLO runtime on 127.0.0.1:8765 (only with CELL_DETECTOR_KEY=yolo26_seg_v1)
#   explain  cl.capstone.explain-agent   EXPLAIN from the report on the host GPU
#
# Without a service argument the command applies to both. Run it from Terminal; launchd runs
# scripts/host_service.py with the .venv-metal interpreter, which needs Full Disk Access (~/Desktop).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/malaria_dl_local_project/.venv-metal/bin/python"
AGENTS="$HOME/Library/LaunchAgents"
LOGS="$HOME/Library/Logs/Capstone"
DOMAIN="gui/$(id -u)"

label() { case "$1" in yolo) echo cl.capstone.yolo-detector ;; explain) echo cl.capstone.explain-agent ;; esac; }
plist() { echo "$AGENTS/$(label "$1").plist"; }
log() { echo "$LOGS/$(label "$1").log"; }
loaded() { launchctl print "$DOMAIN/$(label "$1")" >/dev/null 2>&1; }

xml() { local value="${1//&/&amp;}"; value="${value//</&lt;}"; printf '%s' "${value//>/&gt;}"; }

write_plist() {
  local service="$1"
  mkdir -p "$AGENTS" "$LOGS"
  cat > "$(plist "$service")" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$(label "$service")</string>
  <key>ProgramArguments</key>
  <array>
    <string>$(xml "$PYTHON")</string>
    <string>$(xml "$ROOT/scripts/host_service.py")</string>
    <string>$service</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>ProcessType</key><string>Interactive</string>
  <key>EnvironmentVariables</key><dict><key>PYTHONUNBUFFERED</key><string>1</string></dict>
  <key>StandardOutPath</key><string>$(xml "$(log "$service")")</string>
  <key>StandardErrorPath</key><string>$(xml "$(log "$service")")</string>
</dict>
</plist>
EOF
  plutil -lint -s "$(plist "$service")"
}

install_one() {
  [ -x "$PYTHON" ] || { echo "No existe $PYTHON (crea .venv-metal primero)." >&2; exit 1; }
  write_plist "$1"
  loaded "$1" && launchctl bootout "$DOMAIN/$(label "$1")" 2>/dev/null || true
  launchctl bootstrap "$DOMAIN" "$(plist "$1")"
  echo "$(label "$1"): instalado y cargado."
}

status_one() {
  local name; name="$(label "$1")"
  if ! loaded "$1"; then echo "$name: no cargado (scripts/host_services.sh start $1)"; return; fi
  launchctl print "$DOMAIN/$name" | awk -v n="$name" '/^\tstate =|^\tpid =|^\tlast exit code =/ {gsub(/^\t/, ""); print n ": " $0}'
  if [ -f "$(log "$1")" ]; then
    tail -n 3 "$(log "$1")" | sed "s/^/  /"
    if tail -n 50 "$(log "$1")" | grep -q "Operation not permitted\|HOST_SERVICE_PERMISSION_DENIED"; then
      echo "  ⚠ macOS bloqueó el acceso a ~/Desktop. Concede \"Acceso total al disco\" a:"
      echo "    $("$PYTHON" -c 'import os,sys; print(os.path.realpath(sys.executable))' 2>/dev/null || echo "$PYTHON")"
      echo "    y luego: scripts/host_services.sh restart $1"
    fi
  fi
}

run() {
  local command="$1" service="$2"
  case "$command" in
    install) install_one "$service" ;;
    start) if loaded "$service"; then launchctl kickstart "$DOMAIN/$(label "$service")"; echo "$(label "$service"): iniciado."; else install_one "$service"; fi ;;
    restart) loaded "$service" || install_one "$service"; launchctl kickstart -k "$DOMAIN/$(label "$service")"; echo "$(label "$service"): reiniciado." ;;
    stop) launchctl bootout "$DOMAIN/$(label "$service")" 2>/dev/null && echo "$(label "$service"): detenido (sigue instalado; vuelve al iniciar sesión)." || echo "$(label "$service"): no estaba cargado." ;;
    uninstall) launchctl bootout "$DOMAIN/$(label "$service")" 2>/dev/null || true; rm -f "$(plist "$service")"; echo "$(label "$service"): desinstalado." ;;
    status) status_one "$service" ;;
    logs) tail -n 50 "$(log "$service")" 2>/dev/null || echo "Sin registros en $(log "$service")." ;;
    *) echo "uso: $0 install|start|status|restart|stop|uninstall|logs [yolo|explain]" >&2; exit 64 ;;
  esac
}

command="${1:-status}"
case "${2:-all}" in
  all) for service in yolo explain; do run "$command" "$service"; done ;;
  yolo|explain) run "$command" "$2" ;;
  *) echo "servicio desconocido: $2 (yolo|explain)" >&2; exit 64 ;;
esac
