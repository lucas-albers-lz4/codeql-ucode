#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
python3 "$ROOT/scripts/m4-wol-query-local-smoke.py"
