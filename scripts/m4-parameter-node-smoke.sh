#!/usr/bin/env bash
# M4 gate: ParameterNode from named formals that have a CFG node, and
# argument-to-parameter via Call.getArgument + ParameterPosition.
# Not call resolution, not production taint. Production LocalTaint /
# RequestArgsExec stay on Models. Not path_found.
# viableSourceCallable stays none().
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-parameter-node"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/ParameterNode.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile ParameterNode smoke =="
codeql query compile "$Q" --search-path="$QLPATH"

echo "== compile production LocalTaint / RequestArgsExec (still Models) =="
codeql query compile "$LOCAL" --search-path="$QLPATH"
codeql query compile "$REQ" --search-path="$QLPATH"

for q in "$LOCAL" "$REQ"; do
	if ! grep -q 'import codeql.ucode.m3.Models' "$q"; then
		echo "production query lost Models import: $q" >&2
		exit 1
	fi
done

if ! grep -q 'none() // TODO' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "viableSourceCallable lost none() TODO" >&2
	exit 1
fi

if grep -n 'summaryStoreStep\|summaryReadStep' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowPrivate.qll; then
	echo "parameter node wired summary steps" >&2
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

echo "== ParameterNode =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/params.bqrs"
codeql bqrs decode --format=csv "$DB/params.bqrs" | tee "$DB/params.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-parameter-node/params.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)

def has(msg):
	return msg in msgs

for msg in [
	"param 0:param in ssa_pos",
	"param 0:request in ssa_pos",
	"param 1:b in ssa_pos",
	"param 0:arrowx in ssa_pos",
	"param 0:arrowa in ssa_pos",
	"param 1:arrowb in ssa_pos",
	"param 0:arrowxs in ssa_pos",
	"param 0:s in luci",
	"param 0:i in luci",
	"param 1:n in luci",
	"param 0:port in luci",
	"arg-param 0 in ssa_pos",
	"arg-param 0 in luci",
]:
	if not has(msg):
		sys.exit(f"missing ParameterNode/arg-param {msg}: {blob}")

if any("path_found" in m or "setInitAction" in m for m in msgs):
	sys.exit("ParameterNode smoke scored taint/path_found: " + blob)
print("ParameterNode pos/neg ok")
PY

echo "M4 ParameterNode smoke passed"
