#!/usr/bin/env bash
# Experimental variable binding and value-flow declaration-order control.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
OUT="$ROOT/.codeql-database/m4-variable-order"
SRC="$OUT/src/ql/test/extractor-smoke"
DB="$OUT/db"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
[[ -x "$PACK/tools/linux64/extractor" ]] || { echo 'build extractor pack first' >&2; exit 1; }
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
rm -rf "$OUT"
mkdir -p "$SRC"
cp ql/test/variable-order/order.uc "$SRC/order.uc"
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files "$DB" --language=ucode --include='**/*.uc' --working-dir="$SRC"
cp "$DB/trap/ucode/routing.json" "$OUT/routing.json"
codeql database finalize "$DB"
for pair in 'diagnostics/SuccessfullyExtractedFiles extracted' 'diagnostics/ExtractionErrors errors' 'extractor-smoke/VariableOrderBindings bindings' 'extractor-smoke/VariableOrderFlow flow'; do
  read -r query name <<< "$pair"
  codeql query run "$ROOT/ql/src/$query.ql" --database="$DB" --search-path="$QLPATH" --threads=1 --ram=2048 --output="$OUT/$name.bqrs"
  codeql bqrs decode --format=json --entities=url,string "$OUT/$name.bqrs" > "$OUT/$name.json"
done
python3 scripts/variable-order-verify.py "$OUT" "$SRC"
