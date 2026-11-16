#!/usr/bin/env bash
# Focused sameRpcMethod ownership regression with exact entity identities.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-rpc-ownership"
SRC="$ROOT/ql/test/rpc-ownership"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"

source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
  echo "extractor-pack is missing; run scripts/create-extractor-pack.sh first" >&2
  exit 1
fi
python3 - "$SRC" <<'PY'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("rpc_ownership_verify", "scripts/rpc-ownership-verify.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.input_oracle(Path(sys.argv[1]))
PY

rm -rf "$DB"
mkdir -p .codeql-database
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode --include='**/luci' --working-dir="$SRC" "$DB"
cp "$DB/trap/ucode/routing.json" "$DB/routing.json"
python3 - "$DB/routing.json" "$SRC" <<'PY'
import json, pathlib, sys
routing = json.loads(pathlib.Path(sys.argv[1]).read_text())
source = pathlib.Path(sys.argv[2]).resolve()
manifest = json.loads((source.parent / "rpc-ownership-manifest.json").read_text())
paths = {str((source / item["path"]).resolve()) for item in manifest["files"].values()}
expected = {"input_count": 5, "plain_count": 5, "markup_count": 0,
            "markup_inconclusive_count": 0, "uncertain_count": 0,
            "excluded_count": 0, "duplicate_input_count": 0}
if any(routing.get(k) != v for k, v in expected.items()) or len(routing.get("decisions", [])) != 5:
    raise SystemExit(f"unexpected complete routing totals: {routing}")
seen = set()
for row in routing["decisions"]:
    if (row.get("classification"), row.get("reason"), row.get("status"), row.get("installed_path")) != (
            "plain", "rpcd_raw_mode_full_path", "plain_route_selected", "usr/share/rpcd/ucode/luci"):
        raise SystemExit(f"unexpected route: {row}")
    seen.add(row.get("path"))
if seen != paths:
    raise SystemExit(f"routing source identities differ: missing={paths-seen}, extra={seen-paths}")
print("PASS routing: exactly five intended plain fixture identities")
PY

codeql database finalize "$DB"
run_json() {
  local query="$1" name="$2"
  codeql query run "$ROOT/$query" --database="$DB" --search-path="$QLPATH" \
    --threads=1 --ram=2048 --output="$DB/$name.bqrs"
  codeql bqrs decode --format=json --entities=url,string "$DB/$name.bqrs" > "$DB/$name.json"
}
run_json ql/src/diagnostics/SuccessfullyExtractedFiles.ql extracted
run_json ql/src/diagnostics/ExtractionErrors.ql errors
run_json ql/src/m4/RpcOwnershipControlsTest.ql RpcOwnershipControlsTest
run_json ql/src/m4/RequestArgsExec.ql RequestArgsExec.ql
run_json ql/src/m3/LocalTaint.ql LocalTaint.ql
python3 - "$DB" "$SRC" <<'PY'
import importlib.util, json, pathlib, sys
out, source = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]).resolve()
spec = importlib.util.spec_from_file_location("rpc_ownership_verify", "scripts/rpc-ownership-verify.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.input_oracle(source)
expected = sorted(str(path.relative_to(source)) for path in source.rglob("luci"))
extracted = module.file_identities(json.loads((out / "extracted.json").read_text()), source, expected)
observed = sorted(extracted)
if observed != expected:
    raise SystemExit(f"successful extraction identities differ: {observed} != {expected}")
errors = module.tuples(json.loads((out / "errors.json").read_text()))
if errors:
    raise SystemExit(f"extraction errors are not empty: {errors}")
module.verify(source, out)
PY
python3 scripts/rpc-ownership-mutation.py "$DB" "$SRC" "$DB"

echo "M4 RPC ownership smoke passed"
