#!/usr/bin/env bash
# M4 gate: extract luci.sys (sys.uc) and assert init_action reaches builtin system.
# Does not change the M1/M3 extract sets.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-sys"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

rm -rf "$DB"
mkdir -p .codeql-database

echo "== index sys.uc =="
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/sys.uc' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

csv_rows() {
	codeql bqrs decode --format=csv "$1" | tail -n +2 | grep -c . || true
}

runq() {
	local q="$1" out="$2"
	codeql query run "$q" --database="$DB" --search-path="$QLPATH" --output="$out"
}

echo "== SuccessfullyExtractedFiles == 1 (sys.uc) =="
runq "$ROOT/ql/src/diagnostics/SuccessfullyExtractedFiles.ql" "$DB/extracted.bqrs"
codeql bqrs decode --format=csv "$DB/extracted.bqrs" | tee "$DB/extracted.csv"
extracted="$(csv_rows "$DB/extracted.bqrs")"
if [[ "$extracted" -ne 1 ]]; then
	echo "expected count(SuccessfullyExtractedFiles) == 1, got $extracted" >&2
	exit 1
fi
python3 - <<'PY'
import csv, sys
from pathlib import Path
rows = list(csv.DictReader(open(".codeql-database/m4-sys/extracted.csv")))
names = {Path(r["f"]).name for r in rows}
if names != {"sys.uc"}:
	sys.exit(f"extracted basenames {names} != {{'sys.uc'}}")
print("extracted basenames", sorted(names))
PY

echo "== InitActionSystem == 1 =="
runq "$ROOT/ql/src/m4/InitActionSystem.ql" "$DB/init.bqrs"
codeql bqrs decode --format=csv "$DB/init.bqrs" | tee "$DB/init.csv"
if [[ "$(csv_rows "$DB/init.bqrs")" -ne 1 ]]; then
	echo "expected InitActionSystem rows == 1" >&2
	codeql bqrs decode --format=csv "$DB/init.bqrs"
	exit 1
fi
python3 - <<'PY'
import csv, sys
rows = list(csv.reader(open(".codeql-database/m4-sys/init.csv")))
msgs = " ".join(r[1] for r in rows[1:])
if "builtin system" not in msgs:
	sys.exit("missing builtin system: " + msgs)
if "not a modeled sanitizer" not in msgs:
	sys.exit("missing sanitizer disclaimer: " + msgs)
print("init_action system row ok")
print(msgs)
PY

echo "M4 luci.sys init_action smoke passed"
