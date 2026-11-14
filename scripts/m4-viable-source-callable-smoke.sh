#!/usr/bin/env bash
# M4 gate: unique same-file identifier and member-property
# FunctionDeclarations resolve as source CfgScopes. Builtin identifier
# system and imported fs popen / basename / access / open / readfile
# resolve as library callables. Imported luci.sys / library member
# callees (read/close) stay unresolved.
# Production LocalTaint / RequestArgsExec stay on Models. Not
# path_found. jumpStep uses unfiltered simpleIdentifierCall and unique
# same-file member FunctionDeclarations. In-file SSA localFlowStep+
# still reaches builtin system on ssa_pos. Summary through-flow stays
# none().
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-viable-source-callable"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/ViableSourceCallable.ql"
FLOW="$ROOT/ql/src/extractor-smoke/LocalFlowStep.ql"
PROD="$ROOT/ql/src/m4/SsaReachesSystem.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs

echo "== compile viableSourceCallable smoke =="
codeql query compile "$Q" --search-path="$QLPATH"
codeql query compile "$FLOW" --search-path="$QLPATH"
codeql query compile "$PROD" --search-path="$QLPATH"

echo "== compile production LocalTaint / RequestArgsExec (still Models) =="
codeql query compile "$LOCAL" --search-path="$QLPATH"
codeql query compile "$REQ" --search-path="$QLPATH"

for q in "$LOCAL" "$REQ"; do
	if ! grep -q 'import codeql.ucode.m3.Models' "$q"; then
		echo "production query lost Models import: $q" >&2
		exit 1
	fi
done

if ! grep -q 'uniqueSameFileFunctionDeclaration' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "viableSourceCallable lost same-file FunctionDeclaration resolution" >&2
	exit 1
fi

if ! grep -q 'uniqueSameFileMemberFunctionDeclaration' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "viableSourceCallable lost same-file member FunctionDeclaration resolution" >&2
	exit 1
fi

if grep -q 'none() // TODO' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "viableSourceCallable still none() TODO" >&2
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

if ! grep -q 'BuiltinSystemLibraryCallable' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "viableLibraryCallable lost builtin system" >&2
	exit 1
fi

if ! grep -q 'ImportedFsPopenLibraryCallable' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "viableLibraryCallable lost imported fs popen" >&2
	exit 1
fi

if ! grep -q 'ImportedFsBasenameLibraryCallable' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "viableLibraryCallable lost imported fs basename" >&2
	exit 1
fi

if ! grep -q 'ImportedFsAccessLibraryCallable' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "viableLibraryCallable lost imported fs access" >&2
	exit 1
fi

if ! grep -q 'ImportedFsOpenLibraryCallable' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "viableLibraryCallable lost imported fs open" >&2
	exit 1
fi

if ! grep -q 'ImportedFsReadfileLibraryCallable' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowDispatch.qll; then
	echo "viableLibraryCallable lost imported fs readfile" >&2
	exit 1
fi

if grep -n 'summaryStoreStep\|summaryReadStep\|summaryThroughStep' \
	ql/lib/codeql/ucode/dataflow/internal/DataFlowPrivate.qll; then
	echo "viableSourceCallable wired summary steps" >&2
	exit 1
fi

rm -rf "$DB"
mkdir -p .codeql-database
echo "== index luci ssa_pos sys.uc =="
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/rpcd/ucode/luci' --include='**/ssa_pos' --include='**/sys.uc' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

echo "== ViableSourceCallable =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/viable.bqrs"
codeql bqrs decode --format=csv "$DB/viable.bqrs" | tee "$DB/viable.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-viable-source-callable/viable.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)

def has(msg):
	return msg in msgs

for msg in [
	"shellquote in luci",
	"callPackageVersionCheck in luci",
	"formal_order in ssa_pos",
	"member_order in ssa_pos",
	"library system in ssa_pos",
	"library system in luci",
	"library system in sys.uc",
	"library popen in luci",
	"library popen in sys.uc",
	"library basename in luci",
	"library basename in sys.uc",
	"library access in luci",
	"library open in luci",
	"library open in sys.uc",
	"library readfile in luci",
	"library readfile in sys.uc",
]:
	if not has(msg):
		sys.exit(f"missing same-file or library target {msg}: {blob}")

for bad in [
	"init_action in luci",
	"init_action in sys.uc",
	"system in ssa_pos",
	"popen in luci",
	"popen in sys.uc",
	"basename in luci",
	"basename in sys.uc",
	"access in luci",
	"open in luci",
	"open in sys.uc",
	"readfile in luci",
	"readfile in sys.uc",
	"read in luci",
	"close in luci",
	"library init_action in luci",
	"library init_action in sys.uc",
	"library shellquote in luci",
	"library read in luci",
	"library close in luci",
	"library formal_order in ssa_pos",
	"library member_order in ssa_pos",
]:
	if has(bad):
		sys.exit(f"resolved non-local, imported, or mis-kinded callee {bad}: {blob}")

if any("path_found" in m or "setInitAction" in m for m in msgs):
	sys.exit("viableSourceCallable smoke scored taint/path_found: " + blob)
print("viableSourceCallable pos/neg ok")
PY

echo "== LocalFlowStep (in-file SSA still reaches) =="
codeql query run "$FLOW" --database="$DB" --search-path="$QLPATH" --output="$DB/flow.bqrs"
codeql bqrs decode --format=csv "$DB/flow.bqrs" | tee "$DB/flow.csv"

python3 - <<'PY'
import csv, sys
rows = list(csv.reader(open(".codeql-database/m4-viable-source-callable/flow.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)
if "ssa_pos_src -> ssa_pos_src in ssa_pos" not in msgs:
	sys.exit("missing localFlowStep+ ssa_pos_src -> ssa_pos_src: " + blob)
print("localFlowStep in-file source ok")
PY

echo "== SsaReachesSystem (not luci / setInitAction) =="
codeql query run "$PROD" --database="$DB" --search-path="$QLPATH" --output="$DB/ssaSys.bqrs"
codeql bqrs decode --format=csv "$DB/ssaSys.bqrs" | tee "$DB/ssaSys.csv"

python3 - <<'PY'
import csv, sys
rows = list(csv.reader(open(".codeql-database/m4-viable-source-callable/ssaSys.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)
if "ssa_pos_src reaches system in ssa_pos" not in msgs:
	sys.exit("missing ssa_pos_src reaches system: " + blob)
if any("setInitAction" in m or "init_action" in m or "luci" in m for m in msgs):
	sys.exit("SsaReachesSystem scored luci/setInitAction: " + blob)
print("SsaReachesSystem in-file sink ok")
PY

echo "M4 viableSourceCallable smoke passed"
