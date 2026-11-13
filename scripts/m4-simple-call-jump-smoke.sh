#!/usr/bin/env bash
# M4 gate: jumpStep from same-file identifier Call.getArgument and
# unique same-file member-property FunctionDeclarations into
# ParameterNode. Not production taint. Production LocalTaint /
# RequestArgsExec stay on Models. Not path_found. Call.getIdentifier
# stays identifier-only. Library members, imports, and builtins stay
# unresolved.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-simple-call-jump"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/SimpleCallJump.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile SimpleCallJump smoke =="
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

if grep -n 'summaryStoreStep\|summaryReadStep' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowPrivate.qll; then
	echo "simple-call jump wired summary steps" >&2
	exit 1
fi

if ! grep -q 'simpleIdentifierCall' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "jumpStep lost simpleIdentifierCall" >&2
	exit 1
fi

if ! grep -q 'sameFileJumpCall' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowPrivate.qll; then
	echo "jumpStep lost sameFileJumpCall" >&2
	exit 1
fi

if ! grep -q 'uniqueSameFileMemberFunctionDeclaration' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "sameFileJumpCall lost unique member FunctionDeclaration" >&2
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

echo "== SimpleCallJump =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/jump.bqrs"
codeql bqrs decode --format=csv "$DB/jump.bqrs" | tee "$DB/jump.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-simple-call-jump/jump.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)

def has(msg):
	return msg in msgs

for msg in [
	"jump-param 0:s from shellquote in luci",
	"jump-param 0:pkg from callPackageVersionCheck in luci",
	"jump-param 0:a from formal_order in ssa_pos",
	"jump-param 1:b from formal_order in ssa_pos",
	"jump-param 0:a from member_order in ssa_pos",
	"jump-param 1:b from member_order in ssa_pos",
]:
	if not has(msg):
		sys.exit(f"missing simple-call jumpStep {msg}: {blob}")

if any(
	" in ssa_pos" in m
	and "from formal_order" not in m
	and "from member_order" not in m
	for m in msgs
):
	sys.exit("unexpected ssa_pos jumpStep: " + blob)

if any("from system" in m or "path_found" in m or "setInitAction" in m for m in msgs):
	sys.exit("simple-call jumpStep scored builtin/taint/path_found: " + blob)
print("SimpleCallJump pos/neg ok")
PY

echo "M4 SimpleCallJump smoke passed"
