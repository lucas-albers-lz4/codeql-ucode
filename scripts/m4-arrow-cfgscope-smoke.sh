#!/usr/bin/env bash
# M4 gate: expression-bodied arrow formals get an inner CfgScope with
# CFG nodes and SSA writes, analogous to block-bodied functions.
# Not ParameterNode, not argument/parameter taint, not call resolution.
# Production LocalTaint / RequestArgsExec stay on Models. Not path_found.
# Unique same-file identifier FunctionDeclarations may resolve;
# imported luci.sys stays unresolved.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-arrow-cfgscope"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/ArrowCfgScope.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile ArrowCfgScope smoke =="
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

rm -rf "$DB"
mkdir -p .codeql-database
echo "== index luci ssa_pos =="
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/rpcd/ucode/luci' --include='**/ssa_pos' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

echo "== ArrowCfgScope =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/arrow.bqrs"
codeql bqrs decode --format=csv "$DB/arrow.bqrs" | tee "$DB/arrow.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-arrow-cfgscope/arrow.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)

def has(msg):
	return msg in msgs

for msg in [
	"arrowx in ssa_pos",
	"arrowa in ssa_pos",
	"arrowb in ssa_pos",
	"arrowxs in ssa_pos",
	"i in luci",
	"n in luci",
	"port in luci",
]:
	if not has(msg):
		sys.exit(f"missing expression-arrow Variable+CFG {msg}: {blob}")

if has("s in luci"):
	sys.exit("block-bodied formal s scored as expression-arrow: " + blob)
if has("request in ssa_pos"):
	sys.exit("enclosing function formal request scored as expression-arrow: " + blob)
if has("param in ssa_pos"):
	sys.exit("block-bodied formal param scored as expression-arrow: " + blob)
if any("path_found" in m or "setInitAction" in m for m in msgs):
	sys.exit("ArrowCfgScope smoke scored taint/path_found: " + blob)
print("ArrowCfgScope pos/neg ok")
PY

echo "M4 ArrowCfgScope smoke passed"
