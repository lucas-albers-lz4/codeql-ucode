#!/usr/bin/env bash
# Standalone real extraction and source-provenance table gate.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
PYTHONDONTWRITEBYTECODE=1 python3 -B "$ROOT/scripts/receiver-provenance-smoke.py"
