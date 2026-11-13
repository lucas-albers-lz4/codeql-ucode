#!/usr/bin/env bash
# M4 gate: identity expression-bodied arrows (`x => x`) count the body
# identifier as a VariableReadAccess of the formal, so ParameterNode
# localFlowStep+ reaches that SSA read. Not production taint.
# Production LocalTaint / RequestArgsExec stay on Models. Not
# path_found. Unique same-file identifier FunctionDeclarations may
# resolve separately. jumpStep stays out of localFlowStep.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-identity-arrow"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/IdentityArrow.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile IdentityArrow smoke =="
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
	echo "identity-arrow wired summary steps" >&2
	exit 1
fi

if awk '
	/predicate localFlowStepImpl/,/^  }$/ { if ($0 ~ /jumpStep/) found=1 }
	END { exit found ? 0 : 1 }
' ql/lib/codeql/ucode/dataflow/internal/DataFlowPrivate.qll; then
	echo "jumpStep was wired into localFlowStepImpl" >&2
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

echo "== IdentityArrow =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/identity.bqrs"
codeql bqrs decode --format=csv "$DB/identity.bqrs" | tee "$DB/identity.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-identity-arrow/identity.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)

def has(msg):
	return msg in msgs

for msg in [
	"identity-access identx in ssa_pos",
	"identity-local 0:identx in ssa_pos",
]:
	if not has(msg):
		sys.exit(f"missing identity arrow {msg}: {blob}")

for msg in [
	"identity-access arrowx in ssa_pos",
	"identity-access arrowa in ssa_pos",
	"identity-access arrowb in ssa_pos",
	"identity-access arrowxs in ssa_pos",
	"identity-local 0:arrowx in ssa_pos",
	"identity-access i in luci",
	"identity-access n in luci",
	"identity-access port in luci",
	"identity-access s in luci",
]:
	if has(msg):
		sys.exit("non-identity scored as identity-arrow: " + blob)

if any("path_found" in m or "setInitAction" in m for m in msgs):
	sys.exit("IdentityArrow smoke scored taint/path_found: " + blob)
print("IdentityArrow pos/neg ok")
PY

echo "M4 IdentityArrow smoke passed"
