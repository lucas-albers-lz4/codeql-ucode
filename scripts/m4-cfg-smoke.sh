#!/usr/bin/env bash
# M4 gate: wrapper CFG compiles and a tiny positive/negative fixture runs.
# Does not import CFG into production M3/M4 queries.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-cfg"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/CfgEdges.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile import codeql.ucode.CFG =="
codeql query compile "$Q" --search-path="$QLPATH"

rm -rf "$DB"
mkdir -p .codeql-database
echo "== index cfg_pos cfg_neg =="
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/cfg_pos' --include='**/cfg_neg' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

echo "== CfgEdges =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/cfg.bqrs"
codeql bqrs decode --format=csv "$DB/cfg.bqrs" | tee "$DB/cfg.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-cfg/cfg.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
pos = [m for m in msgs if m.startswith("cfg_pos ->")]
neg = [m for m in msgs if m.startswith("cfg_neg ->")]
cross = [m for m in msgs if m.startswith("cfg_pos -> cfg_neg") or m.startswith("cfg_neg -> cfg_pos")]
if not pos:
	sys.exit("cfg_pos has no CFG successor edges")
if cross:
	sys.exit(f"cross-file CFG edge: {cross[:3]}")
# Two function-expression bodies are distinct CfgScopes; successors must stay inside one.
cross_scope = [m for m in neg if "scopeEq=0" in m]
if cross_scope:
	sys.exit(f"cfg_neg cross-scope successor: {cross_scope[:3]}")
if not neg:
	# Entry/exit edges inside each body still count as same-scope successors.
	sys.exit("cfg_neg has no CFG successor edges (expected intra-scope edges)")
print("cfg_pos edges", len(pos), "cfg_neg edges", len(neg))
PY

echo "M4 CFG smoke passed"
