#!/usr/bin/env bash
# Direct ubus.call syntax inventory, not receiver resolution or taint.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
SRC="$TMP_ROOT/ql/test/extractor-smoke"
mkdir -p "$SRC/usr/share/rpcd/ucode"
cp "$ROOT/ql/test/extractor-smoke/usr/share/rpcd/ucode/luci" "$SRC/usr/share/rpcd/ucode/luci"
# The extractor's existing fixture allowlist includes ssa_pos.
cp "$ROOT/ql/test/extractor-smoke/ubus_call_controls" "$SRC/ssa_pos"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-ubus-call"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	bash scripts/create-extractor-pack.sh
fi
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
rm -rf "$DB"
mkdir -p .codeql-database
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/rpcd/ucode/luci' --include='**/ssa_pos' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"
codeql query run "$ROOT/ql/src/diagnostics/ExtractionErrors.ql" --database="$DB" \
	--search-path="$QLPATH" --output="$DB/errors.bqrs"
codeql bqrs decode --format=csv "$DB/errors.bqrs" > "$DB/errors.csv"
codeql query run "$ROOT/ql/src/m4/UbusCallInventory.ql" --database="$DB" \
	--search-path="$QLPATH" --output="$DB/ubus.bqrs"
codeql bqrs decode --format=csv "$DB/ubus.bqrs" > "$DB/ubus.csv"
python3 - <<'PY'
import csv, sys

errors = list(csv.reader(open('.codeql-database/m4-ubus-call/errors.csv')))[1:]
if errors:
    sys.exit(f'extraction errors in inventory inputs: {errors}')
rows = list(csv.reader(open('.codeql-database/m4-ubus-call/ubus.csv')))[1:]
print(rows)
expected = {'ubus_call fact in luci at line 663',
            'ubus_call fact in luci at line 671',
            'ubus_call fact in ssa_pos at line 2'}
actual = [row[1] for row in rows if len(row) >= 2]
if set(actual) != expected or len(rows) != len(expected):
    sys.exit(f'expected {expected}, got {actual} ({len(rows)} rows)')
print('ubus.call direct member inventory and controls passed')
PY
