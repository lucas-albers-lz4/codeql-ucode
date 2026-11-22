#!/usr/bin/env bash
# Experimental switch-break CFG and public local-expression-flow regression.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
OUT="$ROOT/.codeql-database/m4-switch-break"
SRC="$OUT/src/ql/test/extractor-smoke"
DB="$OUT/db"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
case "$OSTYPE" in
  linux-gnu*) platform=linux64 ;;
  darwin*) platform=osx64 ;;
  *) echo "Unsupported OS: $OSTYPE" >&2; exit 1 ;;
esac
[[ -x "$PACK/tools/$platform/extractor" ]] || { echo 'build extractor pack first' >&2; exit 1; }
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
rm -rf "$OUT"
mkdir -p "$SRC"
cp ql/test/switch-break/*.uc "$SRC/"
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
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
for pair in 'diagnostics/SuccessfullyExtractedFiles extracted' 'diagnostics/ExtractionErrors errors' 'extractor-smoke/SwitchBreakEdges edges' 'extractor-smoke/SwitchBreakFlow flow'; do
  read -r query name <<< "$pair"
  codeql query run "$ROOT/ql/src/$query.ql" --database="$DB" --search-path="$QLPATH" --threads=1 --ram=2048 --output="$OUT/$name.bqrs"
  codeql bqrs decode --format=csv "$OUT/$name.bqrs" > "$OUT/$name.csv"
done
python3 scripts/switch-break-verify.py "$OUT" "$SRC"
