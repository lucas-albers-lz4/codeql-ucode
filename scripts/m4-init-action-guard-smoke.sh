#!/usr/bin/env bash
# Installed-path and export controls for the luci.sys init_action model.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
DB="$ROOT/.codeql-database/m4-init-action-guard"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# This fixture-root suffix makes the extractor recognize the rpcd plugin.
SRC="$TMP/ql/test/extractor-smoke"
mkdir -p "$SRC/usr/share/rpcd/ucode"
cp -R ql/test/init-action-guard/usr "$SRC/"
cp ql/test/extractor-smoke/usr/share/rpcd/ucode/luci "$SRC/usr/share/rpcd/ucode/luci"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	bash scripts/create-extractor-pack.sh
fi
codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null
rm -rf "$DB"
mkdir -p .codeql-database
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/rpcd/ucode/luci' --include='**/sys.uc' --working-dir="$SRC" "$DB"
codeql database finalize "$DB"

for entry in 'diagnostics/SuccessfullyExtractedFiles.ql extracted' \
	'diagnostics/ExtractionErrors.ql errors' \
	'm4/InitActionSystem.ql init' 'm4/InitActionCallerSinkPair.ql pair'; do
	read -r query output <<< "$entry"
	codeql query run "$ROOT/ql/src/$query" --database="$DB" --search-path="$QLPATH" --output="$DB/$output.bqrs"
	codeql bqrs decode --format=csv "$DB/$output.bqrs" > "$DB/$output.csv"
done

python3 - <<'PY'
import csv
from pathlib import Path

db = Path('.codeql-database/m4-init-action-guard')
def rows(name):
    with (db / f'{name}.csv').open() as f:
        return list(csv.reader(f))[1:]

extracted = [row[0] for row in rows('extracted')]
if len(extracted) != 4:
    raise SystemExit(f'expected luci and three control files; got {extracted}')
errors = rows('errors')
if errors:
    raise SystemExit(f'extraction errors: {errors}')
for name in ('init', 'pair'):
    results = rows(name)
    if results:
        raise SystemExit(f'{name} attributed a private or wrong-path function to luci.sys: {results}')
print('private and wrong-path init_action controls produced no luci.sys findings')
PY
