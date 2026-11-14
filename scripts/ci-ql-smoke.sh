#!/usr/bin/env bash
# CI gate: M3 extractor+query smoke, then any M4 smokes present on this ref.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v codeql >/dev/null; then
	echo "codeql CLI not on PATH" >&2
	exit 1
fi

# Readiness belongs to this invocation, never a previous run or caller.
unset CODEQL_UCODE_SMOKE_PACKS_READY
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
export CODEQL_UCODE_SMOKE_PACKS_READY="$ROOT"

echo "== M3 smoke =="
bash scripts/m3-smoke.sh

shopt -s nullglob
m4_scripts=()
for s in scripts/m4-smoke.sh scripts/m4-*-smoke.sh; do
	[[ -f "$s" ]] || continue
	m4_scripts+=("$s")
done
if [[ ${#m4_scripts[@]} -eq 0 ]]; then
	echo "no M4 smoke scripts on this ref (expected until M4 PRs merge)"
	exit 0
fi

for s in "${m4_scripts[@]}"; do
	echo "== $(basename "$s") =="
	bash "$s"
done
