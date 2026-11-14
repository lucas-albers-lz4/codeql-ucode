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

source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs

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

import re
from pathlib import Path

rows = list(csv.reader(open(".codeql-database/m4-cfg/cfg.csv")))
msgs = [r[1] for r in rows[1:] if len(r) > 1]
pattern = re.compile(r"^(\w+):(\d+) -> (\w+):(\d+) scopeEq=([01]) scopeLine=(\d+) kind=(ast|exit) type=(\w+)$")
edges = []
for msg in msgs:
    m = pattern.fullmatch(msg)
    if not m:
        sys.exit(f"unexpected CFG edge format: {msg}")
    src, line, dst, dstline, same, scope, kind, typ = m.groups()
    edges.append((src, int(line), dst, int(dstline), same, int(scope), kind, typ))

def line(fixture, marker):
    lines = Path(f"ql/test/extractor-smoke/{fixture}").read_text().splitlines()
    matches = [i for i, text in enumerate(lines, 1) if marker in text]
    if len(matches) != 1:
        sys.exit(f"expected one {marker} in {fixture}, found {matches}")
    return matches[0]

def has_ast_edge(fixture, before, after):
    return any(src == fixture and n == line(fixture, before) and dst == fixture and
               m == line(fixture, after) and same == "1" and kind == "ast"
               for src, n, dst, m, same, scope, kind, typ in edges)

if any(src != dst or same != "1" for src, _, dst, _, same, _, _, _ in edges):
    sys.exit("cross-file or cross-scope CFG successor")
for fixture, before, after in [
    ("cfg_pos", '"cfg_pos_one"', '"cfg_pos_two"'),
    ("cfg_neg", '"cfg_neg_a"', '"cfg_neg_a_two"'),
    ("cfg_neg", '"cfg_neg_b"', '"cfg_neg_b_two"'),
]:
    if not has_ast_edge(fixture, before, after):
        sys.exit(f"missing statement edge {fixture}: {before} -> {after}")
a_line = line("cfg_neg", '"cfg_neg_a"')
b_line = line("cfg_neg", '"cfg_neg_b"')
a_scopes = {scope for src, n, _, _, _, scope, kind, _ in edges
            if src == "cfg_neg" and n == a_line and kind == "ast"}
b_scopes = {scope for src, n, _, _, _, scope, kind, _ in edges
            if src == "cfg_neg" and n == b_line and kind == "ast"}
if not a_scopes or not b_scopes or a_scopes & b_scopes:
    sys.exit("negative function bodies do not have distinct CFG scopes")
if any(has_ast_edge("cfg_neg", a, b) for a in ('"cfg_neg_a"', '"cfg_neg_a_two"')
       for b in ('"cfg_neg_b"', '"cfg_neg_b_two"')):
    sys.exit("CFG edge crosses negative function bodies")
if has_ast_edge("cfg_pos", "cfg_pos_return", '"cfg_pos_unreachable"'):
    sys.exit("return flows to unreachable statement")
return_line = line("cfg_pos", "cfg_pos_return")
if not any(src == "cfg_pos" and n == return_line and kind == "exit" and typ == "return"
           for src, n, _, _, _, _, kind, typ in edges):
    sys.exit("return has no return-typed edge to scope exit")
print("CFG statement, scope, and return checks passed")
PY

echo "M4 CFG smoke passed"
