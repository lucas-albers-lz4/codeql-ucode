#!/usr/bin/env bash
# Stable source-observation table only; no policy or runtime claim.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
DB="${M4_SETBLOCKDETECT_DB:-$ROOT/.codeql-database/m4-setblockdetect-effect-table}"
QLPATH="${M4_SETBLOCKDETECT_QLPATH:-$PACK:$ROOT/ql/lib:$ROOT/ql/src}"
QLSRC="${M4_SETBLOCKDETECT_QLSRC:-$ROOT/ql/src}"
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
         'negative-import-default', 'negative-extra-argument', 'sibling-shadow',
         'negative-formal-parameter')
for name in names:
    dest = src / 'modules' / name / 'root/usr/share/rpcd/ucode/luci'
    dest.parent.mkdir(parents=True)
    source = luci if name == 'real' else Path('ql/test/effect-controls/setblockdetect') / name / 'usr/share/rpcd/ucode/luci'
    shutil.copyfile(source, dest)
PY
if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	bash scripts/create-extractor-pack.sh
fi
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
rm -rf "$DB"
mkdir -p .codeql-database
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode --include='**/rpcd/ucode/luci' --working-dir="$SRC" "$DB"
codeql database finalize "$DB"
source "$ROOT/scripts/m4-smoke-diagnostics.sh"
M4_DIAGNOSTIC_QLSRC="$QLSRC" check_m4_extraction \
	"$SRC/modules/negative-command/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/negative-extra-argument/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/negative-formal-parameter/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/negative-import-alias/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/negative-import-default/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/negative-import-named/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/negative-member/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/negative-method/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/negative-nonliteral/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/negative-receiver/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/positive/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/positive-renamed-import/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/real/root/usr/share/rpcd/ucode/luci" \
	"$SRC/modules/sibling-shadow/root/usr/share/rpcd/ucode/luci"

for entry in 'm4/SetBlockDetectEffectTable.ql effects'; do
	read -r query output <<< "$entry"
	codeql query run "$QLSRC/$query" --database="$DB" --search-path="$QLPATH" --output="$DB/$output.bqrs"
	codeql bqrs decode --format=csv "$DB/$output.bqrs" > "$DB/$output.csv"
done
python3 - <<'PY'
import csv
import os
from pathlib import Path

db = Path(os.environ.get('M4_SETBLOCKDETECT_DB', '.codeql-database/m4-setblockdetect-effect-table'))
with (db / 'effects.csv').open() as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    rows = list(reader)
want_fields = ['observation_kind', 'method', 'sink_kind', 'command', 'source_path',
               'start_line', 'start_column', 'end_line', 'end_column']
if fields != want_fields:
    raise SystemExit(f'table fields changed: {fields}')
if len(rows) != 5:
    raise SystemExit(f'expected pinned and four positive controls only: {rows}')
for row in rows:
    if (row['observation_kind'], row['method'], row['sink_kind'], row['command']) != (
        'callback_body_call', 'setBlockDetect', 'system', '/sbin/block detect > /etc/config/fstab'):
        raise SystemExit(f'unexpected observation: {row}')
locations = {(row['source_path'], *(int(row[key]) for key in
              ('start_line', 'start_column', 'end_line', 'end_column'))) for row in rows}
expected = {('modules/real/root/usr/share/rpcd/ucode/luci', 532, 21, 532, 68),
            ('modules/positive/root/usr/share/rpcd/ucode/luci', 3, 5, 3, 52),
            ('modules/positive-renamed-import/root/usr/share/rpcd/ucode/luci', 4, 5, 4, 52),
            ('modules/sibling-shadow/root/usr/share/rpcd/ucode/luci', 8, 7, 8, 54),
            ('modules/sibling-shadow/root/usr/share/rpcd/ucode/luci', 14, 5, 14, 52)}
if locations != expected:
    raise SystemExit(f'wrong source locations: {locations} != {expected}')
print('source observations:', rows)
PY
