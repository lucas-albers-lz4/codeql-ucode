#!/usr/bin/env bash
# Production LocalTaint and RequestArgsExec controls in an isolated luci corpus.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$ROOT"
SRC="$ROOT/ql/test/system-binding"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-system-rpc"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
  bash scripts/create-extractor-pack.sh
fi
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
rm -rf "$DB"
mkdir -p .codeql-database
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode --include='**/luci' --working-dir="$SRC" "$DB"
codeql database finalize "$DB"
source "$ROOT/scripts/m4-smoke-diagnostics.sh"
check_m4_extraction "$SRC/usr/share/rpcd/ucode/luci"
for entry in 'm3/LocalTaint.ql local' 'm4/RequestArgsExec.ql rpc'; do
  read -r query output <<< "$entry"
  codeql query run "$ROOT/ql/src/$query" --database="$DB" --search-path="$QLPATH" --output="$DB/$output.bqrs"
  if [[ "$output" == local ]]; then
    codeql bqrs decode --format=json --entities=url "$DB/$output.bqrs" > "$DB/$output.json"
  else
    codeql bqrs decode --format=csv "$DB/$output.bqrs" > "$DB/$output.csv"
  fi
done
python3 - <<'PY'
import csv
import json
from pathlib import Path

db = Path('.codeql-database/m4-system-rpc')
def rows(name):
    with (db / f'{name}.csv').open() as f:
        return list(csv.reader(f))[1:]
local = json.loads((db / 'local.json').read_text())['#select']['tuples']
assert len(local) == 2, local
for row in local:
    src, message, sink, sink_name = row
    assert message == 'request.args reaches system in luci', row
    assert sink_name == 'system', row
    src_url = src['url']
    sink_url = sink['url']
    assert src_url['uri'].endswith('/system-binding/usr/share/rpcd/ucode/luci'), row
    assert sink_url['uri'].endswith('/system-binding/usr/share/rpcd/ucode/luci'), row
    assert sink_url['startLine'] == 11, row
    assert sink_url['startColumn'] == 7 and sink_url['endColumn'] == 34, row
rpc = rows('rpc')
assert len(rpc) == 1 and rpc[0][1] == 'builtin request.args reaches system', rpc
print('production LocalTaint sinks:', [(r[2]['url']['startLine'], r[2]['url']['startColumn'], r[2]['url']['endColumn']) for r in local])
print('RequestArgsExec:', rpc)
PY
