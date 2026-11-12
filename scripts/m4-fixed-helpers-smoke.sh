#!/usr/bin/env bash
# M4 gate: getFeatures.call direct popen/system (not the netifd helper).
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

echo "== GetFeaturesDirectExec =="
codeql query run "$ROOT/ql/src/m4/GetFeaturesDirectExec.ql" \
	--database="$DB" --search-path="$QLPATH" --output="$DB/m4direct.bqrs"
codeql bqrs decode --format=csv "$DB/m4direct.bqrs" | tee "$DB/m4direct.csv"

python3 - <<'PY'
import csv, sys

rows = list(csv.reader(open(".codeql-database/m3-luci/m4direct.csv")))
header, data = rows[0], rows[1:]
msgs = [r[1] for r in data]
kinds = [r[3] for r in data]
lines = []
for m in msgs:
	parts = m.split()
	try:
		lines.append(int(parts[-1]))
	except (ValueError, IndexError):
		sys.exit("bad message: " + m)
want_lines = {268, 275, 278, 294, 315}
if set(lines) != want_lines:
	sys.exit(f"lines {sorted(lines)} != {sorted(want_lines)}")
if kinds.count("popen") != 3:
	sys.exit(f"expected 3 popen, got {kinds.count('popen')}")
if kinds.count("system") != 2:
	sys.exit(f"expected 2 system, got {kinds.count('system')}")
print("getFeatures direct exec", sorted(lines))
PY

echo "M4 fixed-helpers smoke passed"
