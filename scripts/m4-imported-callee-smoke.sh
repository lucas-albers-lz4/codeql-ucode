#!/usr/bin/env bash
# M4 gate: request.args into imported callees (setInitAction → luci.sys init_action).
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

echo "== ImportedCalleeTaint =="
codeql query run "$ROOT/ql/src/m4/ImportedCalleeTaint.ql" \
	--database="$DB" --search-path="$QLPATH" --output="$DB/m4imp.bqrs"
codeql bqrs decode --format=csv "$DB/m4imp.bqrs" | tee "$DB/m4imp.csv"

python3 - <<'PY'
import csv, sys
rows = list(csv.reader(open(".codeql-database/m3-luci/m4imp.csv")))
msgs = [r[1] for r in rows[1:]]
blob = "\n".join(msgs)
if "init_action from 'luci.sys'" not in blob:
	sys.exit("missing init_action from luci.sys: " + blob)
print("imported callee rows", len(msgs))
print(blob)
PY

echo "M4 imported-callee smoke passed"
