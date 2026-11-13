#!/usr/bin/env bash
# M4 gate: storeStep / readStep from extracted member, subscript, object
# and array AST. Not production taint, not localFlowStep, not Future,
# not call resolution. Production LocalTaint / RequestArgsExec stay on
# Models. Not path_found. viableSourceCallable stays none().
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-store-read"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/StoreRead.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile StoreRead smoke =="
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
	echo "store/read wired summary steps" >&2
	exit 1
fi

if grep -n 'storeStep\|readStep' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowPrivate.qll |
	grep -E 'predicate (simpleLocalFlowStep|localFlowStepImpl|localFlowStep)\('; then
	echo "store/read wired into localFlowStep" >&2
	exit 1
fi

rm -rf "$DB"
mkdir -p .codeql-database
echo "== index luci ssa_neg =="
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/rpcd/ucode/luci' --include='**/ssa_neg' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

echo "== StoreRead =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/store-read.bqrs"
codeql bqrs decode --format=csv "$DB/store-read.bqrs" | tee "$DB/store-read.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-store-read/store-read.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)

def has(msg):
	return msg in msgs

for msg in [
	"store Field[field] in ssa_neg",
	"read Field[field] in ssa_neg",
	"read Field[args] in luci",
	"store Element in luci",
	"read Element in luci",
]:
	if not has(msg):
		sys.exit(f"missing store/read {msg}: {blob}")

for m in msgs:
	if m.startswith("Future") or "Future" in m.split():
		sys.exit(f"unexpected Future row {m}: {blob}")
	if not (m.startswith("store Field[") or m.startswith("read Field[") or
		m.startswith("store Element ") or m.startswith("read Element ")):
		sys.exit(f"unexpected StoreRead row {m}: {blob}")
	if "path_found" in m:
		sys.exit("StoreRead smoke scored path_found: " + blob)
print("StoreRead pos/neg ok")
PY

echo "M4 StoreRead smoke passed"
