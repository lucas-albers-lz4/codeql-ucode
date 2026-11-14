#!/usr/bin/env bash
# Actual Models-backed query controls for lexical system binding.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
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
for entry in 'diagnostics/ExtractionErrors.ql errors' 'diagnostics/SuccessfullyExtractedFiles.ql extracted' 'extractor-smoke/ModelsCalleeSinks.ql sinks' 'm4/ShellInjection.ql candidates' 'extractor-smoke/SystemLibraryBinding.ql dispatch'; do
  read -r query output <<< "$entry"
  codeql query run "$ROOT/ql/src/$query" --database="$DB" --search-path="$QLPATH" --output="$DB/$output.bqrs"
  codeql bqrs decode --format=csv "$DB/$output.bqrs" > "$DB/$output.csv"
done
python3 - <<'PY'
import csv
from pathlib import Path

db = Path('.codeql-database/m4-system-lexical')
def rows(name):
    with (db / f'{name}.csv').open() as f:
        return list(csv.reader(f))[1:]
assert not rows('errors'), rows('errors')
extracted = rows('extracted')
assert {Path(row[0]).name for row in extracted} == {'system_lexical.uc', 'system_lexical_import.uc'} and len(extracted) == 2, extracted
sinks = sorted(row[1] for row in rows('sinks'))
candidates = rows('candidates')
dispatch = sorted(row[1] for row in rows('dispatch'))
expected_lines = sorted(['5', '16', '19', '32', '44', '53', '58', '63'])
print('actual sinks:', sinks, 'candidates:', sorted(row[5] for row in candidates), 'dispatch:', dispatch, flush=True)
assert sinks == sorted(f'system at line {line}' for line in expected_lines), sinks
assert sorted(row[5] for row in candidates) == expected_lines, candidates
assert dispatch == expected_lines, dispatch
print('lexical builtin sink and candidate:', sinks, candidates)
PY
