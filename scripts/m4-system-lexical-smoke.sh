#!/usr/bin/env bash
# Actual Models-backed query controls for lexical system binding.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$ROOT"
SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-system-lexical"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
  bash scripts/create-extractor-pack.sh
fi
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
rm -rf "$DB"
mkdir -p .codeql-database
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode --include='**/system_lexical*.uc' --working-dir="$SRC" "$DB"
codeql database finalize "$DB"
source "$ROOT/scripts/m4-smoke-diagnostics.sh"
check_m4_extraction \
  "$SRC/system_lexical.uc" \
  "$SRC/system_lexical_import.uc"

for entry in 'extractor-smoke/ModelsCalleeSinks.ql sinks' 'm4/ShellInjection.ql candidates' 'extractor-smoke/SystemLibraryBinding.ql dispatch'; do
  read -r query output <<< "$entry"
  codeql query run "$ROOT/ql/src/$query" --database="$DB" --search-path="$QLPATH" --output="$DB/$output.bqrs"
  codeql bqrs decode --format=csv "$DB/$output.bqrs" > "$DB/$output.csv"
  if [[ "$output" == sinks || "$output" == candidates || "$output" == dispatch ]]; then
    codeql bqrs decode --format=json --entities=url "$DB/$output.bqrs" > "$DB/$output.json"
  fi
done
python3 - <<'PY'
import csv
import json
from pathlib import Path

db = Path('.codeql-database/m4-system-lexical')
def rows(name):
    with (db / f'{name}.csv').open() as f:
        return list(csv.reader(f))[1:]
sinks = sorted(row[1] for row in rows('sinks'))
candidates = rows('candidates')
dispatch = sorted(row[1] for row in rows('dispatch'))
fixture = Path('ql/test/extractor-smoke/system_lexical.uc').read_text().splitlines()
controls = {'let', 'function', 'parameter', 'rest', 'catch'}
for kind in controls:
    assert sum(f'// sibling builtin: {kind}' in line for line in fixture) == 1, kind
    assert sum(f'// sibling shadow: {kind}' in line for line in fixture) == 1, kind
sibling_lines = [str(i) for i, line in enumerate(fixture, 1) if '// sibling builtin:' in line]
expected_lines = sorted(['5', '16', '19', '32', '44', '53', '58', '63'] + sibling_lines)
print('actual sinks:', sinks, 'candidates:', sorted(row[5] for row in candidates), 'dispatch:', dispatch, flush=True)
assert sinks == sorted(f'system at line {line}' for line in expected_lines), sinks
assert sorted(row[5] for row in candidates) == expected_lines, candidates
assert dispatch == expected_lines, dispatch
expected_sites = {
    (int(line), fixture[int(line) - 1].index('system(') + 1)
    for line in expected_lines
}
for name, index in [('sinks', 0), ('candidates', 2), ('dispatch', 0)]:
    tuples = json.loads((db / f'{name}.json').read_text())['#select']['tuples']
    sites = []
    for row in tuples:
        loc = row[index]['url']
        assert loc['uri'].endswith('/ql/test/extractor-smoke/system_lexical.uc'), row
        sites.append((loc['startLine'], loc['startColumn']))
    assert len(sites) == len(expected_sites) and set(sites) == expected_sites, (name, sites)
    print(f'{name} exact sink sites:', sorted(sites))
print('lexical builtin sink and candidate:', sinks, candidates)
PY
