#!/usr/bin/env bash
set -euxo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-backend-declarations"
QUERY="$ROOT/ql/src/m4/LuciBackendDeclarations.ql"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
SRC="$TMP_ROOT/ql/test/extractor-smoke"
mkdir -p "$SRC/usr/share/rpcd/ucode"
cp ql/test/extractor-smoke/usr/share/rpcd/ucode/luci "$SRC/usr/share/rpcd/ucode/luci"
python3 - "$SRC/usr/share/rpcd/ucode/luci" <<'PY'
import hashlib, sys
if hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest() != '6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e':
    raise SystemExit('pinned luci source hash mismatch')
PY
if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then bash scripts/create-extractor-pack.sh; fi
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
rm -rf "$DB"
mkdir -p .codeql-database
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode --include='**/rpcd/ucode/luci' --working-dir="$SRC" "$DB"
cp "$DB/trap/ucode/routing.json" "$TMP_ROOT/routing.json"
python3 - "$TMP_ROOT/routing.json" "$SRC/usr/share/rpcd/ucode/luci" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
if r['input_count'] != 1 or r['plain_count'] != 1 or len(r['decisions']) != 1:
    raise SystemExit(f'unexpected routing counts: {r}')
row = r['decisions'][0]
if (row['path'] != sys.argv[2] or row['installed_path'] != 'usr/share/rpcd/ucode/luci' or
        row['classification'] != 'plain' or row['reason'] != 'rpcd_raw_mode_full_path'):
    raise SystemExit(f'unexpected routing decision: {row}')
PY
codeql database finalize "$DB"
for entry in "diagnostics/SuccessfullyExtractedFiles.ql extracted" "diagnostics/ExtractionErrors.ql errors"; do
  read -r query output <<< "$entry"
  codeql query run "$ROOT/ql/src/$query" --database="$DB" --search-path="$PACK:$ROOT/ql/lib:$ROOT/ql/src" --output="$DB/$output.bqrs"
  codeql bqrs decode --format=csv "$DB/$output.bqrs" > "$DB/$output.csv"
done
codeql query run "$QUERY" --database="$DB" --search-path="$PACK:$ROOT/ql/lib:$ROOT/ql/src" --output="$DB/table.bqrs"
codeql bqrs decode --format=csv "$DB/table.bqrs" > "$DB/table.csv"
python3 - "$DB" "$SRC/usr/share/rpcd/ucode/luci" <<'PY'
import csv, pathlib, sys
p = pathlib.Path(sys.argv[1])
source = pathlib.Path(sys.argv[2])
def rows(name):
    with (p / name).open(newline='') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)
_, extracted = rows('extracted.csv')
_, errors = rows('errors.csv')
if len(extracted) != 1 or extracted[0].get('f') != str(source) or errors:
    raise SystemExit(f'extraction diagnostics failed: {extracted=} {errors=}')
fields, got = rows('table.csv')
expected_fields = ['observation_kind', 'ubus_object', 'method', 'source_path', 'start_line', 'start_column', 'end_line', 'end_column']
if fields != expected_fields:
    raise SystemExit(f'expected declaration table columns, got {fields}')
with open('ql/test/backend-declarations-real-oracle.csv', newline='') as f:
    expected = list(csv.DictReader(f))
for r in expected:
    r.update(observation_kind='source_declared_callback', ubus_object='luci', source_path='usr/share/rpcd/ucode/luci')
key = lambda r: tuple(r[k] for k in expected_fields)
if sorted(map(key, got)) != sorted(map(key, expected)):
    raise SystemExit(f'declaration identities/spans differ: got={got} expected={expected}')
print(f'verified {len(got)} exact source declarations')
PY
if [[ -n "${M4_BACKEND_EVIDENCE_DIR:-}" ]]; then
  mkdir -p "$M4_BACKEND_EVIDENCE_DIR"
  cp "$TMP_ROOT/routing.json" "$DB"/{extracted.csv,errors.csv,table.csv,extracted.bqrs,errors.bqrs,table.bqrs} "$M4_BACKEND_EVIDENCE_DIR/"
  (cd "$M4_BACKEND_EVIDENCE_DIR" && sha256sum extracted.csv errors.csv table.csv routing.json extracted.bqrs errors.bqrs table.bqrs > sha256.txt)
  sha256sum "$SRC/usr/share/rpcd/ucode/luci" >> "$M4_BACKEND_EVIDENCE_DIR/sha256.txt"
fi
# Never let a developer's selective-control setting weaken the aggregate gate.
unset BACKEND_CONTROL_CASE
python3 scripts/backend-declarations-controls.py
