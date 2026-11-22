#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-fs-binding"
TMP_ROOT="$(mktemp -d)"
TMP_ROOT="$(cd "$TMP_ROOT" && pwd -P)"
trap 'rm -rf "$TMP_ROOT"' EXIT
SRC="$TMP_ROOT/ql/test/extractor-smoke"
mkdir -p "$SRC/usr/share/rpcd/ucode" "$SRC/usr/share/ucode/luci"
cp ql/test/fs-binding-controls/*.uc "$SRC/"
cp ql/test/extractor-smoke/usr/share/rpcd/ucode/luci "$SRC/usr/share/rpcd/ucode/luci"
cp ql/test/extractor-smoke/usr/share/ucode/luci/sys.uc "$SRC/usr/share/ucode/luci/sys.uc"
case "$OSTYPE" in
  linux-gnu*) platform=linux64 ;;
  darwin*) platform=osx64 ;;
  *) echo "Unsupported OS: $OSTYPE" >&2; exit 1 ;;
esac
if [[ ! -x "$PACK/tools/$platform/extractor" ]]; then bash scripts/create-extractor-pack.sh; fi
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
rm -rf "$DB"
mkdir -p .codeql-database
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode --include='**/*.uc' --include='**/rpcd/ucode/luci' --working-dir="$SRC" "$DB"
cp "$DB/trap/ucode/routing.json" "$DB/routing.json"
codeql database finalize "$DB"
for entry in "diagnostics/SuccessfullyExtractedFiles.ql extracted csv" "diagnostics/ExtractionErrors.ql errors json" "m4/FsBindingTargetsTest.ql targets json"; do
  read -r query output format <<< "$entry"
  codeql query run "$ROOT/ql/src/$query" --database="$DB" --search-path="$PACK:$ROOT/ql/lib:$ROOT/ql/src" --output="$DB/$output.bqrs"
  if [[ "$format" == json ]]; then
    codeql bqrs decode --format=json --entities=url,string --output="$DB/$output.json" "$DB/$output.bqrs"
  else
    codeql bqrs decode --format=csv --output="$DB/$output.csv" "$DB/$output.bqrs"
  fi
done
python3 scripts/fs-binding-targets-verify.py "$SRC" "$DB" ql/test/fs-binding-controls/expected.json
# Prove the exact routing-path assertion rejects a receipt with a wrong identity.
python3 - "$SRC" "$DB" ql/test/fs-binding-controls/expected.json "$TMP_ROOT" <<'PYCONTROL'
import json, pathlib, subprocess, sys
src, db, manifest, temp = map(pathlib.Path, sys.argv[1:])
mutated = temp / 'mutated-db'
mutated.mkdir()
route = json.loads((db / 'routing.json').read_text())
route['decisions'][0]['path'] += '.wrong'
(mutated / 'routing.json').write_text(json.dumps(route))
result = subprocess.run([sys.executable, 'scripts/fs-binding-targets-verify.py',
                         str(src), str(mutated), str(manifest)], capture_output=True, text=True)
if result.returncode == 0 or "assert {d['path']" not in result.stderr:
    raise SystemExit(f'routing path mutation was not rejected by the path assertion: {result.stderr}')
print('routing path mutation rejected by exact identity assertion')
PYCONTROL
