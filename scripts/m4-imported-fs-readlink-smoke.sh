#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-imported-fs-readlink"
TMP_ROOT="$(mktemp -d)"
TMP_ROOT="$(cd "$TMP_ROOT" && pwd -P)"
trap 'rm -rf "$TMP_ROOT"' EXIT
SRC="$TMP_ROOT/ql/test/extractor-smoke"
mkdir -p "$SRC/usr/share/rpcd/ucode" "$SRC/usr/share/ucode/luci"
cp ql/test/readlink-controls/*.uc "$SRC/"
cp ql/test/extractor-smoke/usr/share/rpcd/ucode/luci "$SRC/usr/share/rpcd/ucode/luci"
cp ql/test/extractor-smoke/usr/share/ucode/luci/sys.uc "$SRC/usr/share/ucode/luci/sys.uc"
python3 - "$SRC" <<'PY'
from pathlib import Path
import hashlib, sys
src = Path(sys.argv[1])
for name, digest in [('usr/share/rpcd/ucode/luci', '6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e'), ('usr/share/ucode/luci/sys.uc', '0380fba5d843a8950bab0ef70982cb40ab8f475e8d267c873e4199a736b55656')]:
    assert hashlib.sha256((src / name).read_bytes()).hexdigest() == digest, name
PY
source "$ROOT/scripts/smoke-extractor-platform.sh"
platform="$(smoke_extractor_platform "$OSTYPE")"
if [[ ! -x "$PACK/tools/$platform/extractor" ]]; then bash scripts/create-extractor-pack.sh; fi
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
rm -rf "$DB"
mkdir -p .codeql-database
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode --include='**/*.uc' --include='**/rpcd/ucode/luci' --working-dir="$SRC" "$DB"
cp "$DB/trap/ucode/routing.json" "$DB/routing.json"
codeql database finalize "$DB"
for entry in "diagnostics/SuccessfullyExtractedFiles.ql extracted csv" "diagnostics/ExtractionErrors.ql errors json" "m4/ReadlinkTargetsTest.ql targets json"; do
  read -r query output format <<< "$entry"
  codeql query run "$ROOT/ql/src/$query" --database="$DB" --search-path="$PACK:$ROOT/ql/lib:$ROOT/ql/src" --output="$DB/$output.bqrs"
  if [[ "$format" == json ]]; then
    codeql bqrs decode --format=json --entities=url,string --output="$DB/$output.json" "$DB/$output.bqrs"
  else
    codeql bqrs decode --format=csv --output="$DB/$output.csv" "$DB/$output.bqrs"
  fi
done
python3 scripts/readlink-targets-verify.py "$SRC" "$DB" ql/test/readlink-controls/expected.json
# Mutate one real receipt identity and require the unchanged path check to reject it.
python3 - "$SRC" "$DB" ql/test/readlink-controls/expected.json "$TMP_ROOT" <<'PYCONTROL'
import json, pathlib, subprocess, sys
src, db, manifest, temp = map(pathlib.Path, sys.argv[1:])
mutated = temp / 'mutated-db'
mutated.mkdir()
route = json.loads((db / 'routing.json').read_text())
route['decisions'][0]['path'] += '.wrong'
(mutated / 'routing.json').write_text(json.dumps(route))
result = subprocess.run([sys.executable, 'scripts/readlink-targets-verify.py',
                         str(src), str(mutated), str(manifest)], capture_output=True, text=True)
if result.returncode == 0 or "assert {d['path']" not in result.stderr:
    raise SystemExit(f'routing path mutation was not rejected by the path assertion: {result.stderr}')
print('routing path mutation rejected by exact identity assertion')
PYCONTROL
