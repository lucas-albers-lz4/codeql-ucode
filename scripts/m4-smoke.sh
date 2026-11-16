#!/usr/bin/env bash
# M4 gate: luci request.args → popen/system method inventory.
# Reuses the M3 database when present; otherwise runs m3-smoke.sh first.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m3-luci"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"

if [[ ! -d "$DB/db-ucode" ]]; then
	echo "== no M3 database; running m3-smoke.sh =="
	bash scripts/m3-smoke.sh
fi

source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs

echo "== RequestArgsExec luci methods =="
codeql query run "$ROOT/ql/src/m4/RequestArgsExec.ql" \
	--database="$DB" --search-path="$QLPATH" --output="$DB/m4exec.bqrs"
codeql bqrs decode --format=csv "$DB/m4exec.bqrs" | tee "$DB/m4exec.csv"

python3 - <<'PY'
import csv, sys
from collections import Counter

rows = list(csv.DictReader(open(".codeql-database/m3-luci/m4exec.csv")))
msgs = [r.get("col1", "") for r in rows]
methods = {m.split()[0] for m in msgs if m}
want = {
	"getSwconfigFeatures",
	"getSwconfigPortState",
	"getRealtimeStats",
	"setPassword",
	"setLocaltime",
}
if methods != want:
	sys.exit(f"RequestArgsExec methods {sorted(methods)} != {sorted(want)}")
blob = "\n".join(msgs)
for quoted in (
	"getSwconfigFeatures request.args reaches popen via shellquote",
	"getSwconfigPortState request.args reaches popen via shellquote",
	"getRealtimeStats request.args reaches popen via shellquote",
	"setPassword request.args reaches system via shellquote",
):
	if quoted not in blob:
		sys.exit("missing " + quoted)
if "setLocaltime request.args reaches system" not in blob:
	sys.exit("missing setLocaltime system")
if "getFeatures " in blob:
	sys.exit("RequestArgsExec unexpectedly includes getFeatures")
# The quote gate pins how many ShellInjection candidates luci retains; this pins
# which method and sink owns each of those call sites, so a candidate cannot move
# between methods while the totals stay put.
want_counts = {
	("setLocaltime", "system"): 1,
	("getSwconfigFeatures", "popen"): 1,
	("getSwconfigPortState", "popen"): 1,
	("setPassword", "system"): 2,
	("getRealtimeStats", "popen"): 2,
}
counts = Counter((r["col1"].split()[0], r["col3"]) for r in rows if r.get("col1"))
if dict(counts) != want_counts:
	sys.exit(f"RequestArgsExec method/sink distribution {dict(counts)} != {want_counts}")
print("m4 methods", sorted(methods), "rows", len(rows))
PY

echo "== RPC ownership regression (discovered independently by ci-ql-smoke.sh) =="
# The dedicated m4-rpc-ownership-smoke.sh has an isolated database and exact
# source/sink URL oracle; do not duplicate its CI invocation here.

echo "M4 smoke passed"
