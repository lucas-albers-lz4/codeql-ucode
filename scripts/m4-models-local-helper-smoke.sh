#!/usr/bin/env bash
# Models same-file helper attribution and both production consumers.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
python3 "$ROOT/scripts/models-local-helper-smoke.py"
