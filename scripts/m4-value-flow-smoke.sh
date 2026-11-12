#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PACK="$(realpath "$ROOT/extractor-pack")"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
mkdir -p "$TMP/src"
cp "$ROOT/ql/test/extractor-smoke/ssa_value_flow" "$TMP/src/ssa_pos"
codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null
codeql database init "$TMP/db" --language=ucode --search-path="$PACK" --source-root="$TMP/src"
codeql database index-files --language=ucode --include='**/ssa_pos' --working-dir="$TMP/src" "$TMP/db"
codeql database finalize "$TMP/db"
codeql query run "$ROOT/ql/src/extractor-smoke/ValueFlowRegression.ql" --database="$TMP/db" --search-path="$PACK:$ROOT/ql/lib:$ROOT/ql/src" --output="$TMP/out.bqrs"
codeql bqrs decode --format=csv "$TMP/out.bqrs" > "$TMP/out.csv"
codeql query run "$ROOT/ql/src/extractor-smoke/ExprFlowRegression.ql" --database="$TMP/db" --search-path="$PACK:$ROOT/ql/lib:$ROOT/ql/src" --output="$TMP/expr.bqrs"
codeql bqrs decode --format=csv "$TMP/expr.bqrs" > "$TMP/expr.csv"
codeql query run "$ROOT/ql/src/extractor-smoke/ReturnFlowRegression.ql" --database="$TMP/db" --search-path="$PACK:$ROOT/ql/lib:$ROOT/ql/src" --output="$TMP/return.bqrs"
codeql bqrs decode --format=csv "$TMP/return.bqrs" > "$TMP/return.csv"
python3 - "$ROOT/ql/test/extractor-smoke/ssa_value_flow" "$TMP/out.csv" "$TMP/expr.csv" "$TMP/return.csv" <<'PY'
import csv
import sys
from pathlib import Path

lines = Path(sys.argv[1]).read_text().splitlines()
def line(marker):
    matches = [i for i, value in enumerate(lines, 1) if value.rstrip().endswith('// ' + marker)]
    if len(matches) != 1:
        raise ValueError((marker, matches))
    return matches[0]

with open(sys.argv[2], newline='') as stream:
    rows = list(csv.reader(stream))[1:]
flows = set()
for _, value in rows:
    src, dst = value.split(' -> ')
    src_name, src_line = src.split(':')
    dst_name, dst_line, read_line = dst.split(':')
    flows.add((src_name, int(src_line), dst_name, int(dst_line), int(read_line)))

def flow(src_name, src_marker, dst_name, dst_marker, read_marker):
    return (src_name, line(src_marker), dst_name, line(dst_marker), line(read_marker))

expected = [
    ('alias_src', 'alias_src', 'alias_dst', 'alias_dst', 'alias_sink'),
    ('phi_src', 'phi_initial', 'phi_src', 'phi_initial', 'phi_sink'),
    ('phi_src', 'phi_branch', 'phi_src', 'phi_branch', 'phi_sink'),
    ('zero_src', 'zero_initial', 'zero_src', 'zero_initial', 'zero_sink'),
    ('zero_src', 'zero_body', 'zero_src', 'zero_body', 'zero_sink'),
    ('kill_src', 'kill_body', 'kill_dst', 'kill_body', 'kill_sink'),
    ('iter_src', 'iter_src', 'iter_dst', 'iter_body', 'iter_sink'),
    ('short_src', 'short_src', 'short_dst', 'short_write', 'short_sink'),
    ('short_dst', 'short_initial', 'short_dst', 'short_initial', 'short_sink'),
    ('tern_src', 'tern_src', 'tern_dst', 'tern_dst', 'tern_sink'),
    ('for_src', 'for_src', 'for_dst', 'for_body', 'for_sink'),
    ('for_dst', 'for_initial', 'for_dst', 'for_initial', 'for_sink'),
    ('for_infinite_src', 'for_infinite_src', 'for_infinite_dst', 'for_infinite_body', 'for_infinite_sink'),
    ('break_dst', 'break_initial', 'break_dst', 'break_initial', 'break_sink'),
    ('continue_src', 'continue_src', 'continue_dst', 'continue_body', 'continue_sink'),
    ('forin_src', 'forin_src', 'forin_dst', 'forin_body', 'forin_sink'),
    ('forin_dst', 'forin_initial', 'forin_dst', 'forin_initial', 'forin_sink'),
    ('forin_shadow', 'forin_shadow_outer', 'forin_shadow', 'forin_shadow_outer', 'forin_shadow_after'),
    ('forin_existing', 'forin_existing_initial', 'forin_existing', 'forin_existing_initial', 'forin_existing_sink'),
    ('forin_item', 'forin_item_def', 'forin_item', 'forin_item_def', 'forin_item_read'),
    ('switch_src', 'switch_src', 'switch_dst', 'switch_body', 'switch_sink'),
    ('switch_dst', 'switch_initial', 'switch_dst', 'switch_initial', 'switch_sink'),
    ('try_src', 'try_src', 'try_dst', 'try_body', 'try_sink'),
    ('try_dst', 'try_initial', 'try_dst', 'try_initial', 'try_sink'),
    ('catch_shadow', 'catch_shadow_outer', 'catch_shadow', 'catch_shadow_outer', 'catch_shadow_after'),
    ('return_src', 'return_src', 'return_src', 'return_src', 'return_sink'),
    ('logical_preserve', 'logical_preserve', 'logical_preserve', 'logical_preserve', 'logical_preserve_sink'),
    ('logical_src', 'logical_src', 'logical_dst', 'logical_dst', 'logical_sink'),
    ('optional_call', 'optional_call_initial', 'optional_call', 'optional_call_initial', 'optional_call_sink'),
    ('optional_index', 'optional_index_initial', 'optional_index', 'optional_index_initial', 'optional_index_sink'),
    ('optional_member', 'optional_member_initial', 'optional_member', 'optional_member_initial', 'optional_member_sink'),
    ('exception_iteration', 'exception_iteration_initial', 'exception_iteration', 'exception_iteration_initial', 'exception_iteration_sink'),
    ('alt_if_src', 'alt_if_src', 'alt_if_dst', 'alt_if_body', 'alt_if_sink'),
    ('alt_if_dst', 'alt_if_initial', 'alt_if_dst', 'alt_if_initial', 'alt_if_sink'),
    ('alt_elif_src', 'alt_elif_src', 'alt_elif_dst', 'alt_elif_body', 'alt_elif_sink'),
    ('alt_elif_dst', 'alt_elif_initial', 'alt_elif_dst', 'alt_elif_initial', 'alt_elif_sink'),
    ('alt_while_src', 'alt_while_src', 'alt_while_dst', 'alt_while_body', 'alt_while_sink'),
    ('alt_while_dst', 'alt_while_initial', 'alt_while_dst', 'alt_while_initial', 'alt_while_sink'),
    ('alt_for_src', 'alt_for_src', 'alt_for_dst', 'alt_for_body', 'alt_for_sink'),
    ('alt_for_dst', 'alt_for_initial', 'alt_for_dst', 'alt_for_initial', 'alt_for_sink'),
    ('alt_forin_src', 'alt_forin_src', 'alt_forin_dst', 'alt_forin_body', 'alt_forin_sink'),
    ('alt_forin_dst', 'alt_forin_initial', 'alt_forin_dst', 'alt_forin_initial', 'alt_forin_sink'),
    ('alt_shadow', 'alt_shadow_outer', 'alt_shadow', 'alt_shadow_outer', 'alt_shadow_after'),
    ('alt_item', 'alt_item_def', 'alt_item', 'alt_item_def', 'alt_item_read'),
    ('exported_let', 'exported_let_def', 'exported_let', 'exported_let_def', 'exported_let_sink'),
    ('exported_const', 'exported_const_def', 'exported_const', 'exported_const_def', 'exported_const_sink'),
]
forbidden = [
    ('discard_src', 'discard_src', 'discard_dst', 'discard_dst', 'discard_sink'),
    ('independent_src', 'independent_both', 'independent_dst', 'independent_both', 'independent_sink'),
    ('object_src', 'object_src', 'object_dst', 'object_dst', 'object_sink'),
    ('member_src', 'member_src', 'member_dst', 'member_dst', 'member_sink'),
    ('arithmetic_src', 'arithmetic_src', 'arithmetic_dst', 'arithmetic_dst', 'arithmetic_sink'),
    ('overwrite_src', 'overwrite_src', 'overwrite_dst', 'overwrite_body', 'overwrite_sink'),
    ('kill_src', 'kill_initial', 'kill_dst', 'kill_body', 'kill_sink'),
    ('break_src', 'break_src', 'break_dst', 'break_body', 'break_sink'),
    ('forin_shadow', 'forin_shadow_outer', 'forin_shadow', 'forin_shadow_outer', 'forin_shadow_inner'),
    ('catch_shadow', 'catch_shadow_outer', 'catch_shadow', 'catch_shadow_outer', 'catch_shadow_inner'),
    ('alt_shadow', 'alt_shadow_outer', 'alt_shadow', 'alt_shadow_outer', 'alt_shadow_inner'),
    ('for_infinite_dst', 'for_infinite_initial', 'for_infinite_dst', 'for_infinite_initial', 'for_infinite_sink'),
]
errors = [f'missing {case}' for case in expected if flow(*case) not in flows]
errors += [f'unexpected {case}' for case in forbidden if flow(*case) in flows]
with open(sys.argv[3], newline='') as stream:
    expr_rows = list(csv.reader(stream))[1:]
expr_flows = set()
for _, value in expr_rows:
    source, sink = value.split(' -> ')
    name, sink_line = sink.split(':')
    expr_flows.add((int(source), name, int(sink_line)))
expr_expected = [
    ('alias_src', 'alias_dst', 'alias_sink'),
    ('phi_initial', 'phi_src', 'phi_sink'),
    ('zero_initial', 'zero_src', 'zero_sink'),
    ('iter_src', 'iter_dst', 'iter_sink'),
    ('short_src', 'short_dst', 'short_sink'),
    ('tern_src', 'tern_dst', 'tern_sink'),
    ('for_src', 'for_dst', 'for_sink'),
    ('for_infinite_src', 'for_infinite_dst', 'for_infinite_sink'),
    ('forin_src', 'forin_dst', 'forin_sink'),
    ('forin_existing_initial', 'forin_existing', 'forin_existing_sink'),
    ('switch_src', 'switch_dst', 'switch_sink'),
    ('try_src', 'try_dst', 'try_sink'),
    ('return_src', 'return_src', 'return_sink'),
    ('logical_preserve', 'logical_preserve', 'logical_preserve_sink'),
    ('logical_src', 'logical_dst', 'logical_sink'),
    ('optional_call_initial', 'optional_call', 'optional_call_sink'),
    ('optional_index_initial', 'optional_index', 'optional_index_sink'),
    ('optional_member_initial', 'optional_member', 'optional_member_sink'),
    ('exception_iteration_initial', 'exception_iteration', 'exception_iteration_sink'),
    ('alt_if_src', 'alt_if_dst', 'alt_if_sink'),
    ('alt_elif_src', 'alt_elif_dst', 'alt_elif_sink'),
    ('alt_while_src', 'alt_while_dst', 'alt_while_sink'),
    ('alt_for_src', 'alt_for_dst', 'alt_for_sink'),
    ('alt_forin_src', 'alt_forin_dst', 'alt_forin_sink'),
    ('exported_let_def', 'exported_let', 'exported_let_sink'),
    ('exported_const_def', 'exported_const', 'exported_const_sink'),
]
expr_forbidden = [
    ('discard_src', 'discard_dst', 'discard_sink'),
    ('independent_both', 'independent_dst', 'independent_sink'),
    ('object_src', 'object_dst', 'object_sink'),
    ('member_src', 'member_dst', 'member_sink'),
    ('arithmetic_src', 'arithmetic_dst', 'arithmetic_sink'),
    ('overwrite_src', 'overwrite_dst', 'overwrite_sink'),
    ('kill_initial', 'kill_dst', 'kill_sink'),
    ('break_src', 'break_dst', 'break_sink'),
    ('forin_shadow_outer', 'forin_shadow', 'forin_shadow_inner'),
    ('catch_shadow_outer', 'catch_shadow', 'catch_shadow_inner'),
    ('alt_shadow_outer', 'alt_shadow', 'alt_shadow_inner'),
    ('try_kill_src', 'try_kill_dst', 'try_kill_sink'),
]
for source_marker, name, sink_marker in expr_expected:
    if (line(source_marker), name, line(sink_marker)) not in expr_flows:
        errors.append(f'missing expression flow {source_marker} -> {name} at {sink_marker}')
for source_marker, name, sink_marker in expr_forbidden:
    if (line(source_marker), name, line(sink_marker)) in expr_flows:
        errors.append(f'unexpected expression flow {source_marker} -> {name} at {sink_marker}')
with open(sys.argv[4], newline='') as stream:
    return_rows = list(csv.reader(stream))[1:]
return_flows = {tuple(map(int, row[1].split(' -> '))) for row in return_rows}
if (line('return_src'), line('return_sink')) not in return_flows:
    errors.append('missing source expression -> return value flow')
if (line('return_discard_src'), line('return_discard_sink')) in return_flows:
    errors.append('unexpected discarded source expression -> return value flow')
if (line('return_logical_src'), line('return_logical_sink')) not in return_flows:
    errors.append('missing logical short-circuit expression -> return value flow')
if errors:
    sys.exit('\n'.join(errors))
print('value-flow regressions passed')
PY
