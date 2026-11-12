#!/usr/bin/env bash
# M4 gate: getBlockDevices popen, setBlockDetect system, setLocaltime sysfixtime.
# Inventory only. Not request.args taint. Not setInitAction path_found.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m3-luci"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"

# Reject changed fixtures before extraction; line numbers refer to this snapshot.
python3 - <<'PY'
import hashlib
import re
from pathlib import Path

root = Path("ql/test/extractor-smoke")
pin = re.search(r"^sha256: ([0-9a-f]{64})$", (root / "SOURCE.txt").read_text(), re.M)
source = root / "usr/share/rpcd/ucode/luci"
if pin is None or hashlib.sha256(source.read_bytes()).hexdigest() != pin[1]:
    raise SystemExit("luci fixture does not match SOURCE.txt sha256")
PY

# Always reindex current sources instead of trusting a previously finalized DB.
echo "== fresh M3 database =="
bash scripts/m3-smoke.sh

codeql pack install "$ROOT/ql/lib" >/dev/null
codeql pack install "$ROOT/ql/src" >/dev/null

echo "== BlockDeviceExec =="
codeql query run "$ROOT/ql/src/m4/BlockDeviceExec.ql" \
	--database="$DB" --search-path="$QLPATH" --output="$DB/m4block.bqrs"
codeql bqrs decode --format=csv "$DB/m4block.bqrs" | tee "$DB/m4block.csv"

python3 - <<'PY'
import csv
from collections import Counter

with open(".codeql-database/m3-luci/m4block.csv") as f:
    rows = list(csv.reader(f))[1:]
actual = Counter((r[3], r[4], r[5], int(r[1].rsplit(" ", 1)[1])) for r in rows)
expected = Counter({
    ("getBlockDevices", "popen", "/sbin/block info 2>/dev/null", 481): 1,
    ("setBlockDetect", "system", "/sbin/block detect > /etc/config/fstab", 532): 1,
    ("setLocaltime", "system", "/etc/init.d/sysfixtime restart >/dev/null", 112): 1,
})
if actual != expected:
    raise SystemExit(f"block-device tuples {actual} != {expected}")
if any("path_found" in r[1] for r in rows):
    raise SystemExit("must not claim path_found")
print("block-device exec", sorted(actual.elements()))
PY

echo "M4 block-device smoke passed"
