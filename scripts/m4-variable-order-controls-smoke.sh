#!/usr/bin/env bash
# Additional declaration-order controls: exact identities and extraction.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
OUT="$ROOT/.codeql-database/m4-variable-order-controls"
SRC="$OUT/src/ql/test/extractor-smoke"
DB="$OUT/db"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
[[ -x "$PACK/tools/linux64/extractor" ]] || { echo 'build extractor pack first' >&2; exit 1; }
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
python3 scripts/variable-order-controls-verify.py inputs "$ROOT/ql/test/variable-order-controls"
rm -rf "$OUT"
mkdir -p "$SRC"
cp ql/test/variable-order-controls/*.uc "$SRC/"
python3 scripts/variable-order-controls-verify.py inputs "$SRC"
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
# Preserve routing even if indexing fails.
if codeql database index-files "$DB" --language=ucode --include='**/*.uc' --working-dir="$SRC"; then
  cp "$DB/trap/ucode/routing.json" "$OUT/routing.json"
else
  rc=$?
  if [[ -f "$DB/trap/ucode/routing.json" ]]; then
    cp "$DB/trap/ucode/routing.json" "$OUT/routing.json" || echo 'failed to retain routing' >&2
  fi
  exit "$rc"
fi
codeql database finalize "$DB"
for pair in 'diagnostics/SuccessfullyExtractedFiles extracted' 'diagnostics/ExtractionErrors errors' 'extractor-smoke/VariableOrderControls bindings'; do
  read -r query name <<< "$pair"
  codeql query run "$ROOT/ql/src/$query.ql" --database="$DB" --search-path="$QLPATH" --threads=1 --ram=2048 --output="$OUT/$name.bqrs"
  codeql bqrs decode --format=json --entities=url,string "$OUT/$name.bqrs" > "$OUT/$name.json"
done
python3 scripts/variable-order-controls-verify.py results "$OUT" "$SRC"
