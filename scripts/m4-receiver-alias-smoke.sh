#!/usr/bin/env bash
# Fresh extracted alias controls with an exact source-span oracle.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
PYTHONDONTWRITEBYTECODE=1 python3 -B "$ROOT/scripts/m4-receiver-alias-smoke.py"
