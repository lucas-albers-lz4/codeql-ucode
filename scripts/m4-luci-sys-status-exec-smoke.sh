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

source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs

rm -rf "$DB"
mkdir -p .codeql-database
echo "== index luci sys.uc =="
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
		--include='**/rpcd/ucode/luci' --include='**/sys.uc' \
		--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

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
expected = {
    "getProcessList via process_list popen /bin/busybox top -bn1 at line 7",
    "getConntrackList via conntrack_list popen /usr/sbin/conntrack -L -o extended at line 49",
}
if set(msgs) != expected:
    sys.exit(f"unexpected dispatch/helper/command/line tuples: {msgs}")
if any("path_found" in m for m in msgs):
    sys.exit("must not claim path_found")
print("luci.sys status exec tuples", sorted(msgs))
PY

# Each modified source tree is indexed afresh. The first swaps dispatches; the
# second changes both the fixed command and the fallback guard. Neither can
# produce an inventory row, despite preserving helper and wrapper names.
NEG_ROOT="$(mktemp -d)"
trap 'rm -rf "$NEG_ROOT"' EXIT
for variant in dispatch evidence; do
    variant_src="$NEG_ROOT/$variant/src"
    variant_db="$NEG_ROOT/$variant/db"
    mkdir -p "$variant_src/usr/share/rpcd/ucode" "$variant_src/usr/share/ucode/luci"
    cp "$SRC/usr/share/rpcd/ucode/luci" "$variant_src/usr/share/rpcd/ucode/luci"
    cp "$SRC/usr/share/ucode/luci/sys.uc" "$variant_src/usr/share/ucode/luci/sys.uc"
    python3 - "$variant" "$variant_src" <<'PYNEG'
import pathlib, sys
variant, root = sys.argv[1], pathlib.Path(sys.argv[2])
if variant == "dispatch":
    p = root / "usr/share/rpcd/ucode/luci"
    s = p.read_text().replace("return { result: conntrack_list() };", "return { result: SWAPPED() };")
    s = s.replace("return { result: process_list() };", "return { result: conntrack_list() };")
    s = s.replace("return { result: SWAPPED() };", "return { result: process_list() };")
else:
    p = root / "usr/share/ucode/luci/sys.uc"
    s = p.read_text().replace("popen('/bin/busybox top -bn1')", "popen('/bin/busybox top -bn1; true')")
    s = s.replace("if (! nfct) {", "if (nfct) {")
p.write_text(s)
PYNEG
    codeql database init "$variant_db" --language=ucode --search-path="$PACK" --source-root="$variant_src"
    codeql database index-files --language=ucode --include='**/rpcd/ucode/luci' --include='**/sys.uc' \
        --working-dir="$variant_src" "$variant_db"
    codeql database finalize "$variant_db"
    codeql query run "$ROOT/ql/src/m4/LuciSysStatusExec.ql" --database="$variant_db" \
        --search-path="$QLPATH" --output="$variant_db/result.bqrs"
    codeql bqrs decode --format=csv "$variant_db/result.bqrs" > "$variant_db/result.csv"
    python3 - "$variant" "$variant_db/result.csv" <<'PYCHECK'
import csv, sys
rows = list(csv.reader(open(sys.argv[2])))
if len(rows) != 1:
    sys.exit(f"{sys.argv[1]} negative control returned rows: {rows[1:]}")
print(sys.argv[1], "negative control: no rows")
PYCHECK
done

echo "M4 luci.sys status exec smoke passed"
