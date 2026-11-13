#!/usr/bin/env bash
# M4 gate: FlowSummary / FlowSource / FlowSink / ModelsAsData / Concepts
# typecheck on dataflow 1.1.6. Import smoke only. Summaries do not attach to
# calls. ActiveThreatModelSource is uninhabited (no Range models). Production LocalTaint /
# RequestArgsExec stay on Models. Not path_found. viableSourceCallable stays
# none().
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PACK="$ROOT/extractor-pack"
QLPATH="$ROOT/ql/lib:$ROOT/ql/src"
if [[ -d "$PACK" ]]; then
	QLPATH="$PACK:$QLPATH"
fi

SMOKE="$ROOT/ql/src/extractor-smoke/FlowSummaryCompile.ql"
LOCAL="$ROOT/ql/src/m3/LocalTaint.ql"
REQ="$ROOT/ql/src/m4/RequestArgsExec.ql"

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== compile FlowSummary / Concepts import smoke =="
codeql query compile "$SMOKE" --search-path="$QLPATH"

echo "== compile production LocalTaint / RequestArgsExec (still Models) =="
codeql query compile "$LOCAL" --search-path="$QLPATH"
codeql query compile "$REQ" --search-path="$QLPATH"

for q in "$LOCAL" "$REQ"; do
	if grep -E 'dataflow\.FlowSummary|ucode\.Concepts' "$q"; then
		echo "production query imported FlowSummary/Concepts: $q" >&2
		exit 1
	fi
	if ! grep -q 'import codeql.ucode.m3.Models' "$q"; then
		echo "production query lost Models import: $q" >&2
		exit 1
	fi
done

echo "M4 FlowSummary compile smoke passed"
