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
	--include='**/quote_*' \
	--working-dir="$SRC" "$DB"
codeql database finalize "$DB"

runq() {
	codeql query run "$1" --database="$DB" --search-path="$QLPATH" --output="$2"
}

echo "== CompleteQuotedArg =="
runq "$ROOT/ql/src/m4/CompleteQuotedArg.ql" "$DB/quoted.bqrs"
codeql bqrs decode --format=csv "$DB/quoted.bqrs" | tee "$DB/quoted.csv"

echo "== ShellquoteTemplateShape (not a barrier) =="
runq "$ROOT/ql/src/m4/ShellquoteTemplateShape.ql" "$DB/shape.bqrs"
codeql bqrs decode --format=csv "$DB/shape.bqrs" > "$DB/shape.csv"

echo "== ShellInjection =="
runq "$ROOT/ql/src/m4/ShellInjection.ql" "$DB/inject.bqrs"
codeql bqrs decode --format=csv "$DB/inject.bqrs" | tee "$DB/inject.csv"

python3 - <<'PY'
import csv, re, sys
from collections import Counter
from pathlib import Path

def msgs(path):
	rows = list(csv.reader(open(path)))
	return [r[1] for r in rows[1:]]

def pairs(path):
	"""(message, sink name) per result row: the message names only the fixture."""
	rows = list(csv.reader(open(path)))
	return [(r[1], r[3] if len(r) > 3 else "") for r in rows[1:]]

quoted = msgs(".codeql-database/m4-quote/quoted.csv")
inject = msgs(".codeql-database/m4-quote/inject.csv")
inject_pairs = pairs(".codeql-database/m4-quote/inject.csv")
shape = msgs(".codeql-database/m4-quote/shape.csv")

# Match the complete fixture basename, not a substring: e.g. quote_ok must
# not be satisfied by quote_ok_echo.uc, nor quote_bad_separator by its variant.
def fixture_names(messages, pattern):
    names = set()
    for message in messages:
        match = re.fullmatch(pattern, message)
        if not match:
            sys.exit(f"Unexpected query message: {message}")
        names.add(match.group(1))
    return names

shape_names = fixture_names(shape, r"supported template shape in (.+)")
inject_names = fixture_names(
    inject, r"shell-injection candidate via \S+ in (.+?)(?: \(quoted executable selection\))?"
)
if quoted:
    sys.exit("No shellquote implementation currently has proven trusted semantics")
bad_controls = [p.name for p in Path("ql/test/extractor-smoke").glob("quote_bad_*")]
for good in ("quote_ok", "quote_ok_echo.uc", "quote_ok_printf.uc"):
    if good not in shape_names or good not in inject_names:
        sys.exit(f"Expected supported shape but unknown semantics for {good}")
for bad in bad_controls:
    if bad in shape_names or bad not in inject_names:
        sys.exit(f"Must reject shape and retain candidate for {bad}")
# The real luci fixture calls a local shellquote helper whose semantics are not
# modeled, so its request.args to popen/system candidates must be retained. The
# message carries only the fixture basename, so pin the retained set by sink; a
# lost candidate changes the counts. Method identity for the same call sites is
# asserted separately by scripts/m4-smoke.sh (RequestArgsExec rows for
# getSwconfigFeatures / getSwconfigPortState "via shellquote").
luci_sinks = Counter(sink for message, sink in inject_pairs if message.endswith(" in luci"))
if luci_sinks != Counter({"popen": 4, "system": 3}):
    sys.exit(f"Expected 7 retained luci candidates (4 popen, 3 system), got {dict(luci_sinks)}")
if "luci" in shape_names:
    sys.exit("Local luci helper must not pass the unresolved binding check")
if "taint_pos" not in inject_names:
    sys.exit("ShellInjection missing unquoted taint_pos")
if not any(re.fullmatch(r"shell-injection candidate via \S+ in quote_exe \(quoted executable selection\)", m) for m in inject):
    sys.exit("ShellInjection missing quote_exe executable-selection candidate")
if "taint_neg" in inject_names:
    sys.exit("ShellInjection unexpectedly includes taint_neg")
print("quote barrier controls ok")
print("quoted:\n", "\n".join(quoted))
print("inject:\n", "\n".join(inject))
PY

echo "M4 quote smoke passed"
