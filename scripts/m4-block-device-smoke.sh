#!/usr/bin/env bash
# M4 gate: getBlockDevices popen, setBlockDetect system, setLocaltime sysfixtime.
# Inventory only. Not request.args taint. Not setInitAction path_found.
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

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== BlockDeviceExec =="
codeql query run "$ROOT/ql/src/m4/BlockDeviceExec.ql" \
	--database="$DB" --search-path="$QLPATH" --output="$DB/m4block.bqrs"
codeql bqrs decode --format=csv "$DB/m4block.bqrs" | tee "$DB/m4block.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m3-luci/m4block.csv")))
header, data = rows[0], rows[1:]
msgs = [r[1] for r in data]
kinds = [r[3] for r in data]
lines = []
methods = []
for m in msgs:
	parts = m.split()
	methods.append(parts[0])
	try:
		lines.append(int(parts[-1]))
	except (ValueError, IndexError):
		sys.exit("bad message: " + m)
want_lines = {112, 481, 532}
if set(lines) != want_lines:
	sys.exit(f"lines {sorted(lines)} != {sorted(want_lines)}")
if 111 in lines:
	sys.exit("date system at line 111 is not the sysfixtime sink")
if methods.count("getBlockDevices") != 1 or kinds.count("popen") != 1:
	sys.exit(f"expected one getBlockDevices popen, got methods={methods} kinds={kinds}")
if methods.count("setBlockDetect") != 1:
	sys.exit(f"expected one setBlockDetect, got {methods}")
if methods.count("setLocaltime") != 1:
	sys.exit(f"expected one setLocaltime sysfixtime, got {methods}")
if "path_found" in " ".join(msgs):
	sys.exit("must not claim path_found")
print("block-device exec", sorted(lines), methods)
PY

echo "M4 block-device smoke passed"
