#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
python3 "$ROOT/scripts/m4-wol-query-local-smoke.py"
