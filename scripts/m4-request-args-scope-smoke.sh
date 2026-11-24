#!/usr/bin/env bash
# Synthetic path-eligibility regression. Requires an existing extractor pack and installed QL packs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/ql/test/request-args-scope"
PACK="$ROOT/extractor-pack"
cd "$ROOT"
# Resolve once before the shared installer, which invokes `codeql` through PATH.
CODEQL="${CODEQL:-$(command -v codeql)}"
[[ -x "$CODEQL" && -f "$CODEQL" ]] || { echo 'CodeQL executable not found' >&2; exit 1; }
CODEQL="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$CODEQL")"
[[ "${CODEQL##*/}" == codeql ]] || { echo 'resolved CodeQL executable must be named codeql' >&2; exit 1; }
export PATH="${CODEQL%/*}:$PATH"
hash -r
[[ "$(command -v codeql)" == "$CODEQL" ]] || { echo 'CodeQL PATH resolution mismatch' >&2; exit 1; }
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
python3 "$ROOT/scripts/request-args-scope-verify.py" --preflight "$SRC"
if [[ -n "${REQUEST_ARGS_SCOPE_OUT:-}" ]]; then
  # mkdir without -p reserves the requested output name atomically.
  mkdir "$REQUEST_ARGS_SCOPE_OUT"
  OUT="$(cd "$REQUEST_ARGS_SCOPE_OUT" && pwd -P)"
else
  OUT="$(mktemp -d "${TMPDIR:-/tmp}/request-args-scope.XXXXXX")"
fi
printf 'Evidence directory: %s\n' "$OUT"
DB="$OUT/db"
"$CODEQL" version | tee "$OUT/codeql-version.txt"
"$CODEQL" database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
CODEQL_UCODE_STAGED_ROOT="$SRC" "$CODEQL" database index-files "$DB" --language=ucode --include='**/*.uc' --working-dir="$SRC"
cp "$DB/trap/ucode/routing.json" "$OUT/routing.json"
"$CODEQL" database finalize "$DB"
run_query() {
  local query="$1" name="$2"
  "$CODEQL" query run "$query" --database="$DB" --search-path="$PACK:$ROOT/ql/lib:$ROOT/ql/src" --threads=1 --ram=2048 --output="$OUT/$name.bqrs"
  "$CODEQL" bqrs decode --format=json --entities=url,string "$OUT/$name.bqrs" > "$OUT/$name.json"
}
cd "$ROOT"
run_query "$ROOT/ql/src/diagnostics/SuccessfullyExtractedFiles.ql" extracted
run_query "$ROOT/ql/src/diagnostics/ExtractionErrors.ql" errors
run_query "$ROOT/ql/src/extractor-smoke/RequestArgsScopeInventory.ql" inventory
run_query "$ROOT/ql/src/m4/RequestArgsExec.ql" request
MUTANT_DIR="$(mktemp -d "$ROOT/ql/src/m4/RequestArgsScopeMutant.XXXXXX")"
trap 'rm -rf "$MUTANT_DIR"' EXIT
MUTANT="$MUTANT_DIR/RequestArgsExec.ql"
python3 - "$ROOT/ql/src/m4/RequestArgsExec.ql" "$MUTANT" <<'PY'
from pathlib import Path
import sys
source = Path(sys.argv[1]).read_text()
needle = '  eligibleSource(src) and\n'
if source.count(needle) != 1:
    raise SystemExit('unexpected query; cannot make path mutation')
Path(sys.argv[2]).write_text(source.replace(needle, '', 1))
PY
run_query "$MUTANT" mutant
python3 "$ROOT/scripts/request-args-scope-verify.py" "$SRC" "$OUT"
