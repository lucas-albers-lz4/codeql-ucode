#!/usr/bin/env bash
# Models-side fs.popen attribution and consumer regression gate.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
python3 "$ROOT/scripts/models-fs-popen-smoke.py"
