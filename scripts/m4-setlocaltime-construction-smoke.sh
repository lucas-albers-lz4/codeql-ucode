#!/usr/bin/env bash
# Serial fresh databases; no assertion here is a security conclusion.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PACK="$ROOT/extractor-pack"
if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then bash scripts/create-extractor-pack.sh; fi
source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs
TMP="$(mktemp -d "${TMPDIR:-/tmp}/setlocaltime-smoke-XXXXXXXX")"
TMP="$(cd "$TMP" && pwd -P)"
trap 'rm -rf "$TMP"' EXIT
SRC="$TMP/ql/test/extractor-smoke"
mkdir -p "$SRC/usr/share/rpcd/ucode"
cp ql/test/extractor-smoke/usr/share/rpcd/ucode/luci "$SRC/usr/share/rpcd/ucode/luci"
python3 - "$SRC/usr/share/rpcd/ucode/luci" <<'PY'
import hashlib, pathlib, sys
if hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest() != '6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e':
    raise SystemExit('source hash mismatch')
PY
DB="$TMP/db"
SEARCH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode --include=usr/share/rpcd/ucode/luci --working-dir="$SRC" "$DB"
cp "$DB/trap/ucode/routing.json" "$TMP/routing.json"
python3 - "$TMP/routing.json" "$SRC/usr/share/rpcd/ucode/luci" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
if (r['input_count'], r['plain_count']) != (1, 1) or len(r['decisions']) != 1:
    raise SystemExit('unexpected routing count')
d = r['decisions'][0]
if (d['path'], d['installed_path'], d['classification'], d['reason']) != (sys.argv[2], 'usr/share/rpcd/ucode/luci', 'plain', 'rpcd_raw_mode_full_path'):
    raise SystemExit('unexpected routing identity')
PY
codeql database finalize "$DB"
for pair in 'diagnostics/SuccessfullyExtractedFiles.ql extracted' 'diagnostics/ExtractionErrors.ql errors' 'm4/SetLocaltimeConstructionTable.ql table'; do
  read -r query name <<< "$pair"
  codeql query run "$ROOT/ql/src/$query" --database="$DB" --search-path="$SEARCH" --output="$TMP/$name.bqrs" --ram=2048 --threads=2
  codeql bqrs decode --format=csv "$TMP/$name.bqrs" > "$TMP/$name.csv"
done
python3 - "$TMP" "$SRC/usr/share/rpcd/ucode/luci" <<'PY'
import csv, pathlib, sys
root = pathlib.Path(sys.argv[1])
def read(name):
    with (root / (name + '.csv')).open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f, strict=True))
extracted = read('extracted')
if len(extracted) != 1 or extracted[0].get('f') != sys.argv[2] or read('errors'):
    raise SystemExit('extraction diagnostics mismatch')
PY
python3 scripts/setlocaltime-construction-verify.py "$TMP/table.csv" ql/test/setlocaltime-construction-real-oracle.csv
# Run unchanged production queries and pin the exact selected candidate identities.
for name in RequestArgsExec ShellInjection; do
  codeql query run "$ROOT/ql/src/m4/$name.ql" --database="$DB" --search-path="$SEARCH" --output="$TMP/$name.bqrs" --ram=2048 --threads=2
  codeql bqrs decode --format=json --entities=url,string "$TMP/$name.bqrs" > "$TMP/$name.json"
done
python3 - "$TMP" "$SRC/usr/share/rpcd/ucode/luci" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1]); uri = pathlib.Path(sys.argv[2]).as_uri()
def loc(x):
    return tuple(x[k] for k in ('startLine', 'startColumn', 'endLine', 'endColumn'))
for name in ('RequestArgsExec', 'ShellInjection'):
    rows = json.loads((root / (name + '.json')).read_text())['#select']['tuples']
    selected = [r for r in rows if ('setLocaltime' in r[1] if name == 'RequestArgsExec' else r[4] == 'setLocaltime')]
    if len(rows) != 7 or len(selected) != 1:
        raise SystemExit(f'{name}: unexpected row count')
    r = selected[0]
    if r[0]['url']['uri'] != uri or r[2]['url']['uri'] != uri or loc(r[0]['url']) != (108,22,108,43) or loc(r[2]['url']) != (111,5,111,118):
        raise SystemExit(f'{name}: wrong exact candidate identities')
print('PASS: production candidates preserved, 7 rows each and exact selected pair')
PY
# Mutants are compiled in a private copy and retain exactly six real query rows.
mkdir -p "$TMP/mutants/ql"
cp .codeqlmanifest.json "$TMP/mutants/"
cp -a ql/lib ql/src "$TMP/mutants/ql/"
python3 - "$TMP/mutants/ql/src/m4" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1]); s = (p / 'SetLocaltimeConstructionTable.ql').read_text()
for name, old, new in [('sink', 'locations_default(sink.getLocation()', 'locations_default(formatter.getLocation()'),
                       ('field', 'locations_default(field.getLocation()', 'locations_default(formatter.getLocation()')]:
    if s.count(old) != 1: raise SystemExit('mutant anchor mismatch')
    (p / ('SetLocaltimeMutant_' + name + '.ql')).write_text(s.replace(old, new))
PY
for kind in sink field; do
  codeql query run "$TMP/mutants/ql/src/m4/SetLocaltimeMutant_$kind.ql" --database="$DB" --search-path="$PACK" --additional-packs="$TMP/mutants/ql/lib:$TMP/mutants/ql/src" --output="$TMP/mutant-$kind.bqrs" --ram=2048 --threads=2
  codeql bqrs decode --format=csv "$TMP/mutant-$kind.bqrs" > "$TMP/mutant-$kind.csv"
  if python3 scripts/setlocaltime-construction-verify.py "$TMP/mutant-$kind.csv" ql/test/setlocaltime-construction-real-oracle.csv > "$TMP/mutant-$kind.verify" 2>&1; then
    echo "oracle accepted wrong-$kind mutant" >&2; exit 1
  fi
done
python3 - "$TMP" <<'PY'
import csv, pathlib, sys
p = pathlib.Path(sys.argv[1])
def rows(name):
    with (p / name).open(newline='', encoding='utf-8') as f: return sorted(csv.DictReader(f, strict=True), key=lambda r: int(r['slot_index']))
base = rows('table.csv')
for kind in ('sink', 'field'):
    mutant = rows('mutant-' + kind + '.csv')
    if len(base) != 6 or len(mutant) != 6: raise SystemExit('mutant changed row count')
    fields = {kind + '_' + suffix for suffix in ('start_line','start_column','end_line','end_column')}
    for a, b in zip(base, mutant):
        if {k for k in a if a[k] != b[k]} - fields or not any(a[k] != b[k] for k in fields):
            raise SystemExit(f'{kind}: wrong mutation boundary')
print('PASS: exact oracle rejects count-preserving sink and field real-query mutants')
PY
python3 scripts/setlocaltime-construction-controls.py
if [[ -n "${M4_SETLOCALTIME_EVIDENCE_DIR:-}" ]]; then
  mkdir -p "$M4_SETLOCALTIME_EVIDENCE_DIR"
  cp "$TMP"/{routing.json,extracted.csv,errors.csv,table.csv,table.bqrs,mutant-sink.csv,mutant-sink.bqrs,mutant-field.csv,mutant-field.bqrs,RequestArgsExec.json,ShellInjection.json} "$M4_SETLOCALTIME_EVIDENCE_DIR/"
fi
