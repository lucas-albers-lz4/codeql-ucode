#!/usr/bin/env bash
# M4 gate: luci request.args → popen/system method inventory.
# Reuses the M3 database when present; otherwise runs m3-smoke.sh first.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m3-luci"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"

if [[ ! -d "$DB/db-ucode" ]]; then
	echo "== no M3 database; running m3-smoke.sh =="
	bash scripts/m3-smoke.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== RequestArgsExec luci methods =="
codeql query run "$ROOT/ql/src/m4/RequestArgsExec.ql" \
	--database="$DB" --search-path="$QLPATH" --output="$DB/m4exec.bqrs"
codeql bqrs decode --format=csv "$DB/m4exec.bqrs" | tee "$DB/m4exec.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.DictReader(open(".codeql-database/m3-luci/m4exec.csv")))
msgs = [r.get("col1", "") for r in rows]
methods = {m.split()[0] for m in msgs if m}
want = {
	"getSwconfigFeatures",
	"getSwconfigPortState",
	"getRealtimeStats",
	"setPassword",
	"setLocaltime",
}
if methods != want:
	sys.exit(f"RequestArgsExec methods {sorted(methods)} != {sorted(want)}")
blob = "\n".join(msgs)
for quoted in (
	"getSwconfigFeatures request.args reaches popen via shellquote",
	"getSwconfigPortState request.args reaches popen via shellquote",
	"getRealtimeStats request.args reaches popen via shellquote",
	"setPassword request.args reaches system via shellquote",
):
	if quoted not in blob:
		sys.exit("missing " + quoted)
if "setLocaltime request.args reaches system" not in blob:
	sys.exit("missing setLocaltime system")
if "getFeatures " in blob:
	sys.exit("RequestArgsExec unexpectedly includes getFeatures")
print("m4 methods", sorted(methods), "rows", len(rows))
PY

echo "== RequestArgsExec same-name cross-file negative =="
XDB="$ROOT/.codeql-database/m4-xfile"
SRC="$ROOT/ql/test/extractor-smoke"
rm -rf "$XDB"
mkdir -p .codeql-database
if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	bash scripts/create-extractor-pack.sh
fi
codeql database init "$XDB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/taint_xfile_a' --include='**/taint_xfile_b' \
	--working-dir="$SRC" "$XDB"
codeql database finalize "$XDB"
codeql query run "$ROOT/ql/src/m4/RequestArgsExec.ql" \
	--database="$XDB" --search-path="$QLPATH" --output="$XDB/m4exec.bqrs"
codeql bqrs decode --format=csv "$XDB/m4exec.bqrs" | tee "$XDB/m4exec.csv"
python3 - <<'PY'
import csv, sys
rows = list(csv.DictReader(open(".codeql-database/m4-xfile/m4exec.csv")))
if rows:
	sys.exit(f"cross-file probe false positive: {rows}")
print("cross-file same-name negative ok")
PY

echo "M4 smoke passed"
