#!/usr/bin/env bash
# Test-only syntactic observation; no taint or dispatcher policy conclusions.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# CI's preceding M3 smoke builds this pack; standalone runs must build it first.
case "$(uname -s)" in
  Linux) platform=linux64 ;;
  Darwin) platform=osx64 ;;
  *) echo "unsupported extractor host" >&2; exit 1 ;;
esac
if [[ ! -x "$ROOT/extractor-pack/tools/$platform/extractor" ]]; then
  echo "extractor pack missing; build it before this standalone smoke" >&2
  exit 1
fi
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
python3 "$ROOT/scripts/dispatcher-formvalue-smoke.py"
