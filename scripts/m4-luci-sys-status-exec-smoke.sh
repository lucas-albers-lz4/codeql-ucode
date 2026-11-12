#!/usr/bin/env bash
# M4 gate: luci.sys conntrack_list/process_list fixed popen for getConntrackList/getProcessList.
# Inventory only. Not request.args taint. Not interprocedural path_found from luci.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-luci-sys-status"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

if [[ ! -d "$DB/db-ucode" ]]; then
	rm -rf "$DB"
	mkdir -p .codeql-database
	echo "== index luci sys.uc =="
	codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
	codeql database index-files --language=ucode \
		--include='**/rpcd/ucode/luci' --include='**/sys.uc' \
		--working-dir="$SRC" "$DB"
	codeql database finalize "$DB"
fi

echo "== LuciSysStatusExec =="
codeql query run "$ROOT/ql/src/m4/LuciSysStatusExec.ql" \
	--database="$DB" --search-path="$QLPATH" --output="$DB/status.bqrs"
codeql bqrs decode --format=csv "$DB/status.bqrs" | tee "$DB/status.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m4-luci-sys-status/status.csv")))
data = rows[1:]
msgs = [r[1] for r in data]
if len(msgs) != 2:
	sys.exit(f"expected 2 rows, got {len(msgs)}: {msgs}")
want_lines = {7, 49}
lines = set()
methods = []
for m in msgs:
	if "path_found" in m:
		sys.exit("must not claim path_found")
	if " via " not in m:
		sys.exit("bad message: " + m)
	rpc, rest = m.split(" via ", 1)
	methods.append(rpc)
	try:
		lines.add(int(rest.rsplit(" ", 1)[-1]))
	except ValueError:
		sys.exit("bad message: " + m)
if lines != want_lines:
	sys.exit(f"lines {sorted(lines)} != {sorted(want_lines)}")
if set(methods) != {"getConntrackList", "getProcessList"}:
	sys.exit(f"rpc methods {methods}")
print("luci.sys status exec", sorted(lines), sorted(methods))
PY

echo "M4 luci.sys status exec smoke passed"
