#!/usr/bin/env bash
# M4 gate: storeStep / readStep from extracted member, subscript, object,
# array, and assignment-post-update AST. Not production taint, not
# localFlowStep, not Future, not call resolution. Production LocalTaint /
# RequestArgsExec stay on Models. Not path_found. Unique same-file
# FunctionDeclarations may resolve; imported luci.sys stays unresolved.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-store-read"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/StoreRead.ql"
SEMANTICS="$ROOT/ql/src/extractor-smoke/StoreReadSemantics.ql"
COMPOSITION="$ROOT/ql/src/extractor-smoke/StoreReadComposition.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs

echo "== compile StoreRead smoke =="
codeql query compile "$Q" --search-path="$QLPATH"
codeql query compile "$SEMANTICS" --search-path="$QLPATH"
codeql query compile "$COMPOSITION" --search-path="$QLPATH"

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

echo "== StoreReadSemantics =="
codeql query run "$SEMANTICS" --database="$DB" --search-path="$QLPATH" --output="$DB/store-read-semantics.bqrs"
codeql bqrs decode --format=csv "$DB/store-read-semantics.bqrs" > "$DB/store-read-semantics.csv"
python3 - <<'PY'
import csv
import sys
from pathlib import Path

fixture = Path("ql/test/extractor-smoke/ssa_neg").read_text().splitlines()
def line(marker):
	matches = [i for i, text in enumerate(fixture, 1) if text.rstrip().endswith("// " + marker)]
	if len(matches) != 1:
		sys.exit(f"expected one {marker}, found {matches}")
	return matches[0]

with open(".codeql-database/m4-store-read/store-read-semantics.csv", newline="") as stream:
	messages = {row[1] for row in list(csv.reader(stream))[1:]}

required = [
	("store Field[probe_field]", "content_field_store"),
	("store Field[]", "content_empty_store"),
	("assign store Field[probe_field]", "content_member_write"),
	("assign store Field[probe_field]", "content_subscript_write"),
	("assign store Element", "content_subscript_write"),
	("read Field[probe_field]", "content_member_compound"),
	("read Field[probe_field]", "content_subscript_compound"),
	("read Field[probe_field]", "content_member_read"),
	("read Field[probe_field]", "content_subscript_read"),
	("read Field[probe_field]", "content_dynamic_read"),
	("read Field[]", "content_empty_read"),
	("read Element", "content_subscript_read"),
]
for label, marker in required:
	message = f"{label}:{line(marker)}"
	if message not in messages:
		sys.exit(f"missing {message}: {sorted(messages)}")

for marker in ["content_member_write", "content_subscript_write", "content_member_delete", "content_subscript_delete"]:
	if any(message.startswith("read ") and message.endswith(f":{line(marker)}") for message in messages):
		sys.exit(f"write-only reference produced a read at {marker}: {sorted(messages)}")
for marker in ["content_member_compound", "content_member_delete", "content_subscript_delete"]:
	if any(message.startswith("assign store ") and message.endswith(f":{line(marker)}") for message in messages):
		sys.exit(f"non-assignment produced an assign store at {marker}: {sorted(messages)}")
for label, marker in [("read Field[probe_field]", "content_other_read"), ("store Field[esckey]", "content_escaped_store")]:
	if f"{label}:{line(marker)}" in messages:
		sys.exit(f"incorrect content identity at {marker}: {sorted(messages)}")
print("StoreRead semantics checks passed")
PY

echo "== StoreReadComposition =="
codeql query run "$COMPOSITION" --database="$DB" --search-path="$QLPATH" --output="$DB/store-read-composition.bqrs"
codeql bqrs decode --format=csv "$DB/store-read-composition.bqrs" > "$DB/store-read-composition.csv"
python3 - <<'PY'
import csv
import sys
from pathlib import Path

fixture = Path("ql/test/extractor-smoke/ssa_neg").read_text().splitlines()
def line(marker):
	matches = [i for i, text in enumerate(fixture, 1) if text.rstrip().endswith("// " + marker)]
	if len(matches) != 1:
		sys.exit(f"expected one {marker}, found {matches}")
	return matches[0]

with open(".codeql-database/m4-store-read/store-read-composition.csv", newline="") as stream:
	messages = {row[1] for row in list(csv.reader(stream))[1:]}
required = [
	("flow", "composed_object_store", "composed_object_read"),
	("flow", "composed_array_store", "composed_array_read"),
	("flow", "composed_inline", "composed_inline"),
	("flow", "shorthand_source", "shorthand_read"),
	("return", "composed_return", "composed_return"),
]
for label, source, sink in required:
	message = f"{label}:{line(source)}:{line(sink)}"
	if message not in messages:
		sys.exit(f"missing {message}: {sorted(messages)}")
for source, sink in [
	("shorthand_source", "shorthand_wrong_field"),
	("shorthand_unrelated", "shorthand_read"),
	("shorthand_source", "shorthand_inner_read"),
]:
	message = f"flow:{line(source)}:{line(sink)}"
	if message in messages:
		sys.exit(f"unexpected {message}: {sorted(messages)}")
print("StoreRead composition checks passed")
PY

echo "M4 StoreRead smoke passed"
