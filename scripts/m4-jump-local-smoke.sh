#!/usr/bin/env bash
# M4 gate: jumpStep ParameterNode continues into SSA localFlowStep.
# Not call resolution, not production taint. Production LocalTaint /
# RequestArgsExec stay on Models. Not path_found.
# viableSourceCallable stays none(). jumpStep stays out of localFlowStep.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-jump-local"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/JumpLocal.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile JumpLocal smoke =="
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
	echo "jump-local wired summary steps" >&2
	exit 1
fi

if ! grep -q 'parameterToSsaDef' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowPrivate.qll; then
	echo "localFlowStep lost parameterToSsaDef" >&2
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

echo "== JumpLocal =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/jump-local.bqrs"
codeql bqrs decode --format=csv "$DB/jump-local.bqrs" | tee "$DB/jump-local.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-jump-local/jump-local.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)

def has(msg):
	return msg in msgs

for msg in [
	"jump-local 0:s from shellquote in luci",
	"jump-local 0:pkg from callPackageVersionCheck in luci",
	"param-local 0:request in ssa_pos",
	"param-local 0:param in ssa_pos",
]:
	if not has(msg):
		sys.exit(f"missing jump/param localFlow {msg}: {blob}")

if any(m.startswith("jump-local ") and m.endswith(" in ssa_pos") for m in msgs):
	sys.exit("jump-local fired without a same-file identifier declaration: " + blob)

if any("from system" in m or "path_found" in m or "setInitAction" in m for m in msgs):
	sys.exit("jump-local scored builtin/taint/path_found: " + blob)
print("JumpLocal pos/neg ok")
PY

echo "M4 JumpLocal smoke passed"
