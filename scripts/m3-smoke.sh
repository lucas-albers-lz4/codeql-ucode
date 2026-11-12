#!/usr/bin/env bash
# M3 gate: extract luci + taint fixtures, then assert query rows.
# M1 luci-only extract remains scripts/m1-smoke.sh (count == 1).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m3-luci"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

rm -rf "$DB"
mkdir -p .codeql-database

echo "== index luci taint_pos taint_neg =="
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/rpcd/ucode/luci' --include='**/taint_pos' --include='**/taint_neg' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

csv_rows() {
	codeql bqrs decode --format=csv "$1" | tail -n +2 | grep -c . || true
}

runq() {
	local q="$1" out="$2"
	codeql query run "$q" --database="$DB" --search-path="$QLPATH" --output="$out"
}

echo "== SuccessfullyExtractedFiles == 3 =="
runq "$ROOT/ql/src/diagnostics/SuccessfullyExtractedFiles.ql" "$DB/extracted.bqrs"
codeql bqrs decode --format=csv "$DB/extracted.bqrs" | tee "$DB/extracted.csv"
extracted="$(csv_rows "$DB/extracted.bqrs")"
if [[ "$extracted" -ne 3 ]]; then
	echo "expected count(SuccessfullyExtractedFiles) == 3, got $extracted" >&2
	exit 1
fi
python3 - <<'PY'
import csv, sys
from pathlib import Path
rows = list(csv.DictReader(open(".codeql-database/m3-luci/extracted.csv")))
names = {Path(r["f"]).name for r in rows}
want = {"luci", "taint_pos", "taint_neg"}
if names != want:
    sys.exit(f"extracted basenames {names} != {want}")
print("extracted basenames", sorted(names))
PY

echo "== ExtractionErrors empty =="
runq "$ROOT/ql/src/diagnostics/ExtractionErrors.ql" "$DB/errors.bqrs"
if [[ "$(csv_rows "$DB/errors.bqrs")" -ne 0 ]]; then
	echo "expected empty ExtractionErrors" >&2
	codeql bqrs decode --format=csv "$DB/errors.bqrs"
	exit 1
fi

echo "== PrintLuciAst still has luci nodes =="
runq "$ROOT/ql/src/extractor-smoke/PrintLuciAst.ql" "$DB/ast.bqrs"
if [[ "$(csv_rows "$DB/ast.bqrs")" -lt 1 ]]; then
	echo "PrintLuciAst returned no luci nodes" >&2
	exit 1
fi

echo "== GetFeaturesPopen == 2 (opkg and apk popen) =="
runq "$ROOT/ql/src/m3/GetFeaturesPopen.ql" "$DB/chain.bqrs"
if [[ "$(csv_rows "$DB/chain.bqrs")" -ne 2 ]]; then
	echo "expected GetFeaturesPopen rows == 2" >&2
	codeql bqrs decode --format=csv "$DB/chain.bqrs"
	exit 1
fi

echo "== GetFeaturesHelperTaint empty (no request.args on netifd helper) =="
runq "$ROOT/ql/src/m3/GetFeaturesHelperTaint.ql" "$DB/helperTaint.bqrs"
if [[ "$(csv_rows "$DB/helperTaint.bqrs")" -ne 0 ]]; then
	echo "expected GetFeaturesHelperTaint empty" >&2
	codeql bqrs decode --format=csv "$DB/helperTaint.bqrs"
	exit 1
fi

echo "== LocalTaint: taint_pos yes, taint_neg no =="
runq "$ROOT/ql/src/m3/LocalTaint.ql" "$DB/taint.bqrs"
codeql bqrs decode --format=csv "$DB/taint.bqrs" | tee "$DB/taint.csv"
python3 - <<'PY'
import csv, sys
rows = list(csv.DictReader(open(".codeql-database/m3-luci/taint.csv")))
msgs = " ".join(r.get("col1", "") for r in rows)
if "taint_pos" not in msgs:
    sys.exit("LocalTaint missing taint_pos")
if "taint_neg" in msgs:
    sys.exit("LocalTaint unexpectedly includes taint_neg")
print("local taint files ok")
PY

echo "== compile production SsaReachesSystem (import DataFlow) =="
codeql query compile "$ROOT/ql/src/m4/SsaReachesSystem.ql" --search-path="$QLPATH"

echo "== SsaReachesSystem empty on M3 luci/taint (ssa fixtures not indexed) =="
runq "$ROOT/ql/src/m4/SsaReachesSystem.ql" "$DB/ssaSys.bqrs"
if [[ "$(csv_rows "$DB/ssaSys.bqrs")" -ne 0 ]]; then
	echo "SsaReachesSystem should be empty on luci/taint; not setInitAction path_found" >&2
	codeql bqrs decode --format=csv "$DB/ssaSys.bqrs"
	exit 1
fi

echo "M3 smoke passed"
