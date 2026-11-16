#!/usr/bin/env bash
# Focused real-extractor and query regression for explicit installed staging roots.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
python3 scripts/staged-routing-controls.py
python3 scripts/staged-routing-query-smoke.py
