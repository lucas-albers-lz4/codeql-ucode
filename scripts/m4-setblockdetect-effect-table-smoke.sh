#!/usr/bin/env bash
# Stable source-observation table only; no policy or runtime claim.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-setblockdetect-effect-table"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
SRC="$TMP_ROOT/src"
python3 - "$SRC" <<'PY'
import hashlib
from pathlib import Path
import re
import shutil
import sys

src = Path(sys.argv[1])
fixture = Path('ql/test/extractor-smoke')
pin = re.search(r'^sha256: ([0-9a-f]{64})$', (fixture / 'SOURCE.txt').read_text(), re.M)
luci = fixture / 'usr/share/rpcd/ucode/luci'
expected_sha = '6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e'
if pin is None or pin[1] != expected_sha or hashlib.sha256(luci.read_bytes()).hexdigest() != expected_sha:
    raise SystemExit('pinned luci fixture hash mismatch')
names = ('real', 'positive', 'positive-renamed-import', 'negative-method',
         'negative-command', 'negative-nonliteral', 'negative-member',
         'negative-receiver', 'negative-import-named', 'negative-import-alias',
         'negative-import-default', 'negative-extra-argument')
for name in names:
    dest = src / 'modules' / name / 'root/usr/share/rpcd/ucode/luci'
    dest.parent.mkdir(parents=True)
    source = luci if name == 'real' else Path('ql/test/effect-controls/setblockdetect') / name / 'usr/share/rpcd/ucode/luci'
    shutil.copyfile(source, dest)
PY
if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	bash scripts/create-extractor-pack.sh
fi
codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null
rm -rf "$DB"
mkdir -p .codeql-database
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode --include='**/rpcd/ucode/luci' --working-dir="$SRC" "$DB"
codeql database finalize "$DB"
for entry in 'diagnostics/SuccessfullyExtractedFiles.ql extracted' \
	'diagnostics/ExtractionErrors.ql errors' 'm4/SetBlockDetectEffectTable.ql effects'; do
	read -r query output <<< "$entry"
	codeql query run "$ROOT/ql/src/$query" --database="$DB" --search-path="$QLPATH" --output="$DB/$output.bqrs"
	codeql bqrs decode --format=csv "$DB/$output.bqrs" > "$DB/$output.csv"
done
python3 - <<'PY'
import csv
from pathlib import Path

db = Path('.codeql-database/m4-setblockdetect-effect-table')
with (db / 'extracted.csv').open() as f:
    extracted = list(csv.DictReader(f))
if len(extracted) != 12:
    raise SystemExit(f'expected all twelve input files extracted: {extracted}')
with (db / 'errors.csv').open() as f:
    errors = list(csv.DictReader(f))
if errors:
    raise SystemExit(f'extraction errors: {errors}')
with (db / 'effects.csv').open() as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    rows = list(reader)
want_fields = ['observation_kind', 'method', 'sink_kind', 'command', 'source_path',
               'start_line', 'start_column', 'end_line', 'end_column']
if fields != want_fields:
    raise SystemExit(f'table fields changed: {fields}')
if len(rows) != 3:
    raise SystemExit(f'expected pinned and two positive controls only: {rows}')
for row in rows:
    if (row['observation_kind'], row['method'], row['sink_kind'], row['command']) != (
        'callback_body_call', 'setBlockDetect', 'system', '/sbin/block detect > /etc/config/fstab'):
        raise SystemExit(f'unexpected observation: {row}')
locations = {(row['source_path'], *(int(row[key]) for key in
              ('start_line', 'start_column', 'end_line', 'end_column'))) for row in rows}
expected = {('modules/real/root/usr/share/rpcd/ucode/luci', 532, 21, 532, 68),
            ('modules/positive/root/usr/share/rpcd/ucode/luci', 3, 5, 3, 52),
            ('modules/positive-renamed-import/root/usr/share/rpcd/ucode/luci', 4, 5, 4, 52)}
if locations != expected:
    raise SystemExit(f'wrong source locations: {locations} != {expected}')
print('source observations:', rows)
PY
