#!/usr/bin/env bash
# M4 gate: Call.getIdentifier is inhabited from extracted function
# fields that are already identifiers. Not ParameterNode, not argument/parameter
# taint, not call resolution. Production LocalTaint / RequestArgsExec
# stay on Models. Not path_found.
# Unique same-file identifier FunctionDeclarations may resolve;
# imported luci.sys stays unresolved.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-call-get-identifier"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/CallGetIdentifier.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile Call.getIdentifier smoke =="
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

echo "== Call.getIdentifier =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/idents.bqrs"
codeql bqrs decode --format=csv "$DB/idents.bqrs" | tee "$DB/idents.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-call-get-identifier/idents.csv")))
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
		sys.exit(f"missing Call.getIdentifier {msg}: {blob}")

for bad in ["read in luci", "close in luci"]:
	if has(bad):
		sys.exit(f"member-callee reported as identifier {bad}: {blob}")

if any("path_found" in m or "setInitAction" in m for m in msgs):
	sys.exit("Call.getIdentifier smoke scored taint/path_found: " + blob)
print("Call.getIdentifier pos/neg ok")
PY

echo "M4 Call.getIdentifier smoke passed"
