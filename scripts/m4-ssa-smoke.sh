#!/usr/bin/env bash
# M4 gate: wrapper SSA/dataflow compiles; production SsaReachesSystem.ql
# requires DataFlow localFlowStep+ from an SSA def node to a read of that
# definition. Isolated SsaReads.ql remains extractor-smoke.
# Public localFlowStep uses SSA identities, not statement CFG nodes.
# Production LocalTaint/RequestArgsExec stay on Models.
# Does not claim setInitAction path_found. Does not treat basename/shellquote
# as sanitizers. viableSourceCallable stays none().
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-ssa"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
Q="$ROOT/ql/src/extractor-smoke/SsaReads.ql"
FLOW="$ROOT/ql/src/extractor-smoke/LocalFlowStep.ql"
PROD="$ROOT/ql/src/m4/SsaReachesSystem.ql"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile import codeql.ucode.DataFlow =="
codeql query compile "$Q" --search-path="$QLPATH"
codeql query compile "$FLOW" --search-path="$QLPATH"
codeql query compile "$PROD" --search-path="$QLPATH"

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
    matches = [i for i, text in enumerate(lines, 1) if text.rstrip().endswith("// " + marker)]
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
for name in ["ssa_same_line", "ssa_sibling"]:
    if not has_pair(name, "ssa_neg", name + "_write", name + "_read"):
        sys.exit(f"missing SSA read for negative system case {name}")
# Check identity, writes/kills, read-before-write updates, and both paths into a phi.
fixture = "ssa_pos"
for name, write, read in [
    ("seq", "seq_decl", "seq_before"),
    ("ssa_multiline", "ssa_multiline_write", "ssa_multiline_read"),
    ("seq", "seq_write", "seq_after"),
    ("seq", "seq_write", "seq_update"),
    ("seq", "seq_update", "seq_updated_read"),
    ("shadow", "shadow_decl", "shadow_outer_read"),
    ("shadow", "shadow_inner_decl", "shadow_inner_read"),
    ("branch", "branch_write", "branch_inner_read"),
    ("branch", "branch_decl", "branch_join_read"),
    ("branch", "branch_write", "branch_join_read"),
    ("both", "both_true", "both_join"),
    ("both", "both_false", "both_join"),
    ("param", "param_decl", "param_outer_read"),
    ("independent", "independent_decl", "independent_read"),
    ("ssa_chain_src", "ssa_chain_src_write", "ssa_chain_copy_write"),
    ("ssa_chain_copy", "ssa_chain_copy_write", "ssa_chain_copy_read"),
]:
    if not has_pair(name, fixture, write, read):
        sys.exit(f"missing SSA pair {name}: {write} -> {read}")
for name, write, read in [
    ("seq", "seq_decl", "seq_after"),
    ("seq", "seq_decl", "seq_write"),
    ("seq", "seq_write", "seq_updated_read"),
    ("shadow", "shadow_decl", "shadow_inner_read"),
    ("shadow", "shadow_inner_decl", "shadow_outer_read"),
    ("both", "both_decl", "both_join"),
    ("param", "param_decl", "param_inner_read"),
]:
    if has_pair(name, fixture, write, read):
        sys.exit(f"unexpected SSA pair {name}: {write} -> {read}")
print("SSA pos/neg access-level checks passed")
PY

echo "== LocalFlowStep =="
codeql query run "$FLOW" --database="$DB" --search-path="$QLPATH" --output="$DB/flow.bqrs"
codeql bqrs decode --format=csv "$DB/flow.bqrs" | tee "$DB/flow.csv"

python3 - <<'PY'
import csv, sys
rows = list(csv.reader(open(".codeql-database/m4-ssa/flow.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)

def has(src, dst, fixture):
    return f"{src} -> {dst} in {fixture}" in msgs

if not has("ssa_pos_src", "ssa_pos_src", "ssa_pos"):
    sys.exit("missing localFlowStep ssa_pos_src -> ssa_pos_src: " + blob)
if not has("ssa_chain_src", "ssa_chain_copy", "ssa_pos"):
    sys.exit("missing identifier-copy localFlowStep ssa_chain_src -> ssa_chain_copy: " + blob)
for src, dst, fixture in [
    ("discarded", "result", "ssa_neg"),
    ("decl_taint", "decl_safe", "ssa_neg"),
    ("obj", "from_field", "ssa_neg"),
    ("skip_src", "skip_safe", "ssa_neg"),
    ("ssa_neg_x", "ssa_neg_y", "ssa_neg"),
]:
    if has(src, dst, fixture):
        sys.exit(f"unsound localFlowStep {src} -> {dst} in {fixture}: " + blob)
print("localFlowStep pos/neg soundness ok")
PY

echo "== SsaReachesSystem =="
codeql query run "$PROD" --database="$DB" --search-path="$QLPATH" --output="$DB/ssaSys.bqrs"
codeql bqrs decode --format=csv "$DB/ssaSys.bqrs" | tee "$DB/ssaSys.csv"

python3 - <<'PY'
import csv, sys
rows = list(csv.reader(open(".codeql-database/m4-ssa/ssaSys.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
blob = "\n".join(msgs)
for name, fixture in [("ssa_pos_src", "ssa_pos"), ("ssa_multiline", "ssa_pos"),
                      ("ssa_neg_y", "ssa_neg")]:
    if f"{name} reaches system in {fixture}" not in msgs:
        sys.exit(f"missing {name} reaches system: " + blob)
for name in ["ssa_neg_x", "ssa_same_line", "ssa_sibling", "discarded",
             "decl_taint", "obj", "skip_src", "ssa_chain_src"]:
    if any(m.startswith(name + " reaches system") for m in msgs):
        sys.exit(f"{name} false positive: " + blob)
if any("setInitAction" in m or "init_action" in m or "luci" in m for m in msgs):
    sys.exit("SsaReachesSystem scored luci/setInitAction: " + blob)
print("SsaReachesSystem pos/neg ok")
PY

echo "M4 SSA smoke passed"
