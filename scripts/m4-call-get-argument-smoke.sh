#!/usr/bin/env bash
# M4 gate: Call.getArgument is inhabited from extracted arguments
# children that are TExpr. Not ParameterNode, not argument/parameter
# taint, not call resolution. Production LocalTaint / RequestArgsExec
# stay on Models. Not path_found.
# Unique same-file identifier and member-property FunctionDeclarations may resolve;
# imported luci.sys stays unresolved.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-call-get-argument"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/CallGetArgument.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs

echo "== compile Call.getArgument smoke =="
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

echo "== Call.getArgument =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/args.bqrs"
codeql bqrs decode --format=csv "$DB/args.bqrs" | tee "$DB/args.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-call-get-argument/args.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)

def has(msg):
	return msg in msgs

for msg in [
	"0:ssa_pos_src in ssa_pos",
	"0:pkg in luci",
	"1:r in luci",
]:
	if not has(msg):
		sys.exit(f"missing Call.getArgument {msg}: {blob}")

if any("path_found" in m or "setInitAction" in m for m in msgs):
	sys.exit("Call.getArgument smoke scored taint/path_found: " + blob)
print("Call.getArgument pos/neg ok")
PY

echo "M4 Call.getArgument smoke passed"
