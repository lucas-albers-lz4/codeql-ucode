#!/usr/bin/env bash
# Exact source-first lexical binding and SSA regression for switch bodies.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
OUT="$ROOT/.codeql-database/m4-switch-scope"
SRC="$OUT/src"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
case "$OSTYPE" in
  linux-gnu*) platform=linux64 ;;
  darwin*) platform=osx64 ;;
  *) echo "Unsupported OS: $OSTYPE" >&2; exit 1 ;;
esac
[[ -x "$PACK/tools/$platform/extractor" ]] || { echo 'build extractor pack first' >&2; exit 1; }
command -v codeql >/dev/null || { echo 'codeql CLI not on PATH' >&2; exit 1; }
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
rm -rf "$OUT"
mkdir -p "$SRC"
cp ql/test/switch-scope/scope.uc "$SRC/scope.uc"
codeql database init "$OUT/db" --language=ucode --search-path="$PACK" --source-root="$SRC"
if codeql database index-files "$OUT/db" --language=ucode --include='**/*.uc' --working-dir="$SRC"; then
  cp "$OUT/db/trap/ucode/routing.json" "$OUT/routing.json"
else
  rc=$?
  if [[ -f "$OUT/db/trap/ucode/routing.json" ]]; then
    cp "$OUT/db/trap/ucode/routing.json" "$OUT/routing.json" || echo 'failed to retain routing' >&2
  fi
  exit "$rc"
fi
codeql database finalize "$OUT/db"
for pair in \
  'diagnostics/SuccessfullyExtractedFiles extracted' \
  'diagnostics/ExtractionErrors errors' \
  'extractor-smoke/SwitchScopeBindings bindings' \
  'extractor-smoke/SwitchScopeFlow flow' \
  'extractor-smoke/SwitchScopeSsa ssa'; do
  read -r query name <<< "$pair"
  codeql query run "$ROOT/ql/src/$query.ql" --database="$OUT/db" \
    --search-path="$QLPATH" --threads=1 --ram=2048 --output="$OUT/$name.bqrs"
  codeql bqrs decode --format=json --entities=url,string "$OUT/$name.bqrs" > "$OUT/$name.json"
done
python3 scripts/switch-scope-verify.py "$OUT"
