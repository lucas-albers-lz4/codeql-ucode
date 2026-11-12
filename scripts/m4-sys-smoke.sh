#!/usr/bin/env bash
# M4 gate: extract luci + luci.sys (sys.uc); init_action system, action tokens, caller/sink pair.
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

echo "== index luci sys.uc =="
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/rpcd/ucode/luci' --include='**/sys.uc' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

csv_rows() {
	codeql bqrs decode --format=csv "$1" | tail -n +2 | grep -c . || true
}

runq() {
	local q="$1" out="$2"
	codeql query run "$q" --database="$DB" --search-path="$QLPATH" --output="$out"
}

echo "== SuccessfullyExtractedFiles == 2 (luci, sys.uc) =="
runq "$ROOT/ql/src/diagnostics/SuccessfullyExtractedFiles.ql" "$DB/extracted.bqrs"
codeql bqrs decode --format=csv "$DB/extracted.bqrs" | tee "$DB/extracted.csv"
extracted="$(csv_rows "$DB/extracted.bqrs")"
if [[ "$extracted" -ne 2 ]]; then
	echo "expected count(SuccessfullyExtractedFiles) == 2, got $extracted" >&2
	exit 1
fi
python3 - <<'PY'
import csv, sys
from pathlib import Path
rows = list(csv.DictReader(open(".codeql-database/m4-sys/extracted.csv")))
names = {Path(r["f"]).name for r in rows}
if names != {"luci", "sys.uc"}:
	sys.exit(f"extracted basenames {names} != {{'luci', 'sys.uc'}}")
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

echo "== SetInitActionActionSwitch == 6 tokens =="
runq "$ROOT/ql/src/m4/SetInitActionActionSwitch.ql" "$DB/switch.bqrs"
codeql bqrs decode --format=csv "$DB/switch.bqrs" | tee "$DB/switch.csv"
python3 - <<'PY'
import csv, sys
rows = list(csv.reader(open(".codeql-database/m4-sys/switch.csv")))
msgs = [r[1] for r in rows[1:]]
tokens = set()
for m in msgs:
	if "action token '" in m:
		tokens.add(m.split("action token '", 1)[1].split("'", 1)[0])
want = {"enable", "disable", "start", "stop", "restart", "reload"}
if tokens != want:
	sys.exit(f"action tokens {tokens} != {want}")
if any("not a sanitizer of name" not in m for m in msgs):
	sys.exit("missing sanitizer disclaimer")
print("setInitAction action tokens", sorted(tokens))
PY

echo "== InitActionCallerSinkPair == 2 (name, action) =="
runq "$ROOT/ql/src/m4/InitActionCallerSinkPair.ql" "$DB/pair.bqrs"
codeql bqrs decode --format=csv "$DB/pair.bqrs" | tee "$DB/pair.csv"
python3 - <<'PY'
import csv, sys
rows = list(csv.reader(open(".codeql-database/m4-sys/pair.csv")))
msgs = [r[1] for r in rows[1:]]
if len(msgs) != 2:
	sys.exit(f"expected 2 pair rows, got {len(msgs)}: {msgs}")
if any("not interprocedural dataflow" not in m for m in msgs):
	sys.exit("missing dataflow disclaimer")
print("caller/sink pair rows", len(msgs))
PY

echo "M4 luci.sys init_action smoke passed"
