#!/usr/bin/env bash

CAPSTONE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

compose() {
  (cd "$CAPSTONE_ROOT" && docker compose "$@")
}
