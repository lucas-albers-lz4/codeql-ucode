#!/usr/bin/env bash
# Direct sink controls; member receivers are not identifier callees.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-models-callee"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	bash scripts/create-extractor-pack.sh
fi
codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null
rm -rf "$DB"
mkdir -p .codeql-database
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode --include='**/models_callee*.uc' --working-dir="$SRC" "$DB"
codeql database finalize "$DB"
for entry in 'diagnostics/ExtractionErrors.ql errors' 'extractor-smoke/ModelsCalleeSinks.ql sinks' 'm4/ShellInjection.ql candidates'; do
	read -r query output <<< "$entry"
	codeql query run "$ROOT/ql/src/$query" --database="$DB" --search-path="$QLPATH" --output="$DB/$output.bqrs"
	codeql bqrs decode --format=csv "$DB/$output.bqrs" > "$DB/$output.csv"
done
python3 - <<'PY'
import csv
from pathlib import Path

db = Path('.codeql-database/m4-models-callee')
def rows(name):
    with (db / f'{name}.csv').open() as f:
        return list(csv.reader(f))[1:]
errors = rows('errors')
if errors:
    raise SystemExit(f'extraction errors: {errors}')
sinks = [row[1] for row in rows('sinks')]
expected = {'popen at line 4', 'system at line 5'}
if len(sinks) != 2 or set(sinks) != expected:
    raise SystemExit(f'expected only direct identifier sinks {expected}; got {sinks}')
candidates = [row[1] for row in rows('candidates')]
if len(candidates) != 2 or not any('via popen' in c for c in candidates) or not any('via system' in c for c in candidates):
    raise SystemExit(f'expected only two direct-call candidates; got {candidates}')
print('direct sinks and candidates:', sinks, candidates)
PY
