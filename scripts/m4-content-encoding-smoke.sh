#!/usr/bin/env bash
# M4 gate: TContent Field/Element is inhabited from extracted member
# properties and subscripts. Not storeStep/readStep, not Future, not
# production taint, not call resolution. Production LocalTaint /
# RequestArgsExec stay on Models. Not path_found. viableSourceCallable
# stays none().
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-content-encoding"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/ContentEncoding.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile ContentEncoding smoke =="
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
echo "== index luci ssa_neg =="
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/rpcd/ucode/luci' --include='**/ssa_neg' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

echo "== ContentEncoding =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/content.bqrs"
codeql bqrs decode --format=csv "$DB/content.bqrs" | tee "$DB/content.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-content-encoding/content.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)

def has(msg):
	return msg in msgs

for msg in [
	"Field[args] in luci",
	"Field[field] in ssa_neg",
	"Element in luci",
]:
	if not has(msg):
		sys.exit(f"missing Content {msg}: {blob}")

for m in msgs:
	if not (m.startswith("Field[") or m.startswith("Element ")):
		sys.exit(f"unexpected ContentEncoding row {m}: {blob}")
print("ContentEncoding pos/neg ok")
PY

echo "M4 ContentEncoding smoke passed"
