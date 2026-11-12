#!/usr/bin/env bash
# M4 gate: wrapper SSA/dataflow compiles and a tiny positive/negative fixture runs.
# Does not import dataflow into production M3/M4 queries.
# Does not claim setInitAction path_found. Does not treat basename/shellquote
# as sanitizers.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-ssa"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/SsaReads.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile import codeql.ucode.DataFlow =="
codeql query compile "$Q" --search-path="$QLPATH"

rm -rf "$DB"
mkdir -p .codeql-database
echo "== index ssa_pos ssa_neg =="
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/ssa_pos' --include='**/ssa_neg' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

echo "== SsaReads =="
codeql query run "$Q" --database="$DB" --search-path="$QLPATH" --output="$DB/ssa.bqrs"
codeql bqrs decode --format=csv "$DB/ssa.bqrs" | tee "$DB/ssa.csv"

python3 - <<'PY'
import csv, sys
from pathlib import Path

rows = list(csv.reader(open(".codeql-database/m4-ssa/ssa.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
pairs = []
for msg in msgs:
    try:
        left, right = msg.split(" -> ", 1)
        name, wline = left.split(":", 1)
        dst, rline = right.split(":", 1)
        pairs.append((name, int(wline), dst, int(rline)))
    except ValueError:
        sys.exit(f"unexpected SSA read format: {msg}")

def line(fixture, marker):
    lines = Path(f"ql/test/extractor-smoke/{fixture}").read_text().splitlines()
    matches = [i for i, text in enumerate(lines, 1) if marker in text]
    if len(matches) != 1:
        sys.exit(f"expected one {marker} in {fixture}, found {matches}")
    return matches[0]

def has_pair(name, fixture, write_marker, read_marker):
    w = line(fixture, write_marker)
    r = line(fixture, read_marker)
    return any(n == name and wl == w and dst == fixture and rl == r
               for n, wl, dst, rl in pairs)

if any(name == "ssa_pos_src" and dst != "ssa_pos" for name, _, dst, _ in pairs):
    sys.exit("ssa_pos_src read crossed files")
if not has_pair("ssa_pos_src", "ssa_pos", "ssa_pos_write", "ssa_pos_read"):
    sys.exit("missing SSA read ssa_pos_src write -> read")
if has_pair("ssa_neg_x", "ssa_neg", "ssa_neg_x_write", "ssa_neg_y_read"):
    sys.exit("ssa_neg_x reached ssa_neg_y_read")
if not has_pair("ssa_neg_y", "ssa_neg", "ssa_neg_y_write", "ssa_neg_y_read"):
    sys.exit("missing SSA read ssa_neg_y write -> read")
print("SSA pos/neg statement-level checks passed")
PY

echo "M4 SSA smoke passed"
