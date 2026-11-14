#!/usr/bin/env bash
# M4 gate: shellquote complete-argument barrier vs unquoted / quoted-executable.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="$ROOT/ql/test/extractor-smoke"
PACK="$ROOT/extractor-pack"
DB="$ROOT/.codeql-database/m4-quote"
QLPATH="$PACK:$ROOT/ql/lib:$ROOT/ql/src"

if [[ ! -x "$PACK/tools/linux64/extractor" ]]; then
	echo "== create-extractor-pack =="
	bash scripts/create-extractor-pack.sh
fi

source "$ROOT/scripts/ql-smoke-pack-install.sh"
install_smoke_packs

rm -rf "$DB"
mkdir -p .codeql-database
echo "== index luci + taint + quote fixtures =="
codeql database init "$DB" --language=ucode --search-path="$PACK" --source-root="$SRC"
codeql database index-files --language=ucode \
	--include='**/luci' --include='**/taint_pos' --include='**/taint_neg' \
	--include='**/quote_ok' --include='**/quote_exe' \
	--include='**/quote_bad_suffix' --include='**/quote_bad_sh_c' --include='**/quote_bad_echo' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

runq() {
	codeql query run "$1" --database="$DB" --search-path="$QLPATH" --output="$2"
}

echo "== CompleteQuotedArg =="
runq "$ROOT/ql/src/m4/CompleteQuotedArg.ql" "$DB/quoted.bqrs"
codeql bqrs decode --format=csv "$DB/quoted.bqrs" | tee "$DB/quoted.csv"

echo "== ShellInjection =="
runq "$ROOT/ql/src/m4/ShellInjection.ql" "$DB/inject.bqrs"
codeql bqrs decode --format=csv "$DB/inject.bqrs" | tee "$DB/inject.csv"

python3 - <<'PY'
import csv, sys

def msgs(path):
	rows = list(csv.reader(open(path)))
	return [r[1] for r in rows[1:]]

quoted = "\n".join(msgs(".codeql-database/m4-quote/quoted.csv"))
inject = "\n".join(msgs(".codeql-database/m4-quote/inject.csv"))

if "quote_ok" not in quoted:
	sys.exit("CompleteQuotedArg missing quote_ok")
if "taint_pos" in quoted or "quote_exe" in quoted or "taint_neg" in quoted:
	sys.exit("CompleteQuotedArg should only be complete template quote")
for bad in ("quote_bad_suffix", "quote_bad_sh_c", "quote_bad_echo"):
	if bad in quoted:
		sys.exit(f"CompleteQuotedArg unexpectedly includes unsupported {bad}")
if "getSwconfigFeatures" not in quoted and "luci" not in quoted:
	# luci getSwconfig* uses the same template pattern
	pass
if "quote_ok" in inject:
	sys.exit("ShellInjection must not include quote_ok (complete-argument barrier)")
if "taint_pos" not in inject:
	sys.exit("ShellInjection missing unquoted taint_pos")
if "quote_exe" not in inject or "quoted executable selection" not in inject:
	sys.exit("ShellInjection missing quote_exe executable-selection candidate")
if "taint_neg" in inject:
	sys.exit("ShellInjection unexpectedly includes taint_neg")
for bad in ("quote_bad_suffix", "quote_bad_sh_c", "quote_bad_echo"):
	if bad not in inject:
		sys.exit(f"ShellInjection must retain unsupported context {bad}")
print("quote barrier controls ok")
print("quoted:\n", quoted)
print("inject:\n", inject)
PY

echo "M4 quote smoke passed"
