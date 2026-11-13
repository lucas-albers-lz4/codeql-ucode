#!/usr/bin/env bash
# M4 gate: FlowSummary getACall matches identifier callees to
# string-keyed summaries. Member callees stay none(). Future stays
# none(). Not production taint, not localFlowStep, not call resolution.
# Production LocalTaint / RequestArgsExec stay on Models. Not path_found.
# Unique same-file identifier FunctionDeclarations may resolve;
# imported luci.sys stays unresolved.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-get-a-call"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/GetACall.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile FlowSummary getACall smoke =="
codeql query compile "$Q" --search-path="$QLPATH"

echo "== compile production LocalTaint / RequestArgsExec (still Models) =="
codeql query compile "$LOCAL" --search-path="$QLPATH"
codeql query compile "$REQ" --search-path="$QLPATH"

for q in "$LOCAL" "$REQ"; do
	if grep -E 'dataflow\.FlowSummary|ucode\.Concepts' "$q"; then
		echo "production query imported FlowSummary/Concepts: $q" >&2
		exit 1
	fi
	if ! grep -q 'import codeql.ucode.m3.Models' "$q"; then
		echo "production query lost Models import: $q" >&2
		exit 1
	fi
done

if grep -n 'summaryLocalStep\|summaryStoreStep\|summaryReadStep\|summaryThroughStep' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowPrivate.qll \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowPublic.qll \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "summary steps wired into localFlowStep / dataflow adapter" >&2
	exit 1
fi

rm -rf "$DB"
mkdir -p .codeql-database
echo "== index luci ssa_pos =="
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/rpcd/ucode/luci' --include='**/ssa_pos' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

echo "== FlowSummary getACall =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/calls.bqrs"
codeql bqrs decode --format=csv "$DB/calls.bqrs" | tee "$DB/calls.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-get-a-call/calls.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)

def has(msg):
	return msg in msgs

for msg in [
	"system in ssa_pos",
	"popen in luci",
	"shellquote in luci",
]:
	if not has(msg):
		sys.exit(f"missing getACall {msg}: {blob}")

for bad in ["member in luci", "member in ssa_pos", "read in luci", "close in luci"]:
	if has(bad):
		sys.exit(f"member-callee returned by getACall {bad}: {blob}")

for m in msgs:
	if m.startswith("Future"):
		sys.exit(f"unexpected Future token {m}: {blob}")

if any("path_found" in m or "setInitAction" in m for m in msgs):
	sys.exit("getACall smoke scored taint/path_found: " + blob)
print("FlowSummary getACall pos/neg ok")
PY

echo "M4 FlowSummary getACall smoke passed"
