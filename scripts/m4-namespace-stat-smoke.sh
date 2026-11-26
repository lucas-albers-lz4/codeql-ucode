#!/usr/bin/env bash
# Source-declared namespace fs regression; selected by ci-ql-smoke.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$ROOT"
source "$ROOT/scripts/smoke-extractor-platform.sh"
platform="$(smoke_extractor_platform "$OSTYPE")"
if [[ ! -x "$ROOT/extractor-pack/tools/$platform/extractor" ]]; then
  echo 'extractor pack missing; build it before this smoke' >&2
  exit 1
fi
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
python3 "$ROOT/scripts/issue155-namespace-ci.py"
