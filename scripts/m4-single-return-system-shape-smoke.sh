#!/usr/bin/env bash
# Bounded lexical observation only; nonmatches have no security interpretation.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
[[ -x "$PACK/tools/linux64/extractor" ]] || bash scripts/create-extractor-pack.sh
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
WORK="$(mktemp -d "${TMPDIR:-/tmp}/single-return-system.XXXXXXXX")"
WORK="$(cd "$WORK" && pwd -P)"
if [[ "${SINGLE_RETURN_KEEP_EVIDENCE:-0}" == 1 ]]; then
  printf 'retained evidence: %s\n' "$WORK"
else
  trap 'rm -rf "$WORK"' EXIT
fi
SRC="$WORK/source"
DB="$WORK/database"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
cases=(comment-positive conditional-expression duplicate-method escaped-literal extra-arg guard-no-call member-guard member methods-alias nested nonliteral positive shadow unknown-helper real)
expected=()
for case in "${cases[@]}"; do
  dst="$SRC/modules/$case/root/usr/share/rpcd/ucode/luci"
  mkdir -p "$(dirname "$dst")"
  if [[ "$case" == real ]]; then
    cp ql/test/extractor-smoke/usr/share/rpcd/ucode/luci "$dst"
    printf '%s  %s\n' 6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e "$dst" | sha256sum -c -
  else
    cp "ql/test/single-return-system/$case.uc" "$dst"
  fi
  expected+=("$dst")
done
codeql database init "$DB" --language=ucode --search-path="$QLPATH" --source-root="$SRC"
status=0
codeql database index-files "$DB" --language=ucode --include='**/rpcd/ucode/luci' --working-dir="$SRC" || status=$?
if ! cp "$DB/trap/ucode/routing.json" "$WORK/routing.json"; then
  printf '%s\n' 'could not retain routing receipt' >&2
  (( status != 0 )) || exit 1
fi
(( status == 0 )) || exit "$status"
codeql database finalize "$DB"
for diagnostic in SuccessfullyExtractedFiles ExtractionErrors; do
  codeql query run "$ROOT/ql/src/diagnostics/$diagnostic.ql" --database="$DB" --search-path="$QLPATH" --output="$DB/$diagnostic.bqrs" --threads=1 --ram=2048
  codeql bqrs decode --format=json --entities=url,string "$DB/$diagnostic.bqrs" > "$DB/$diagnostic.json"
done
python3 -B "$ROOT/scripts/m4-smoke-diagnostics.py" "$DB/SuccessfullyExtractedFiles.json" "$DB/ExtractionErrors.json" "${expected[@]}"
codeql query run "$ROOT/ql/src/m4/SingleReturnFixedSystemSourceShape.ql" --database="$DB" --search-path="$QLPATH" --output="$DB/shape.bqrs" --threads=1 --ram=2048
codeql bqrs decode --format=json --entities=url,string "$DB/shape.bqrs" > "$DB/shape.json"
python3 -B "$ROOT/scripts/single-return-system-oracle.py" "$DB/shape.json"
python3 -B "$ROOT/scripts/single-return-system-controls.py" "$WORK" "$DB"
printf '%s\n' 'PASS bounded source-shape smoke (not an authorization or guard finding)'
