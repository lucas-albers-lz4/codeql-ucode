#!/usr/bin/env bash
# M1 gate: cargo test, pack, extract luci, SuccessfullyExtractedFiles, printAst.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FIXTURE="$ROOT/ql/test/extractor-smoke/usr/share/rpcd/ucode/luci"
if [[ ! -f "$FIXTURE" ]]; then
	echo "missing luci fixture" >&2
	exit 1
fi
if [[ "$(basename "$FIXTURE")" != "luci" ]]; then
	echo "fixture basename is not luci" >&2
	exit 1
fi

echo "== cargo test (parser-load) =="
cargo test -p codeql-extractor-ucode --offline -- --nocapture

echo "== create-extractor-pack =="
bash scripts/create-extractor-pack.sh

PACK="$ROOT/extractor-pack"
SRC="$ROOT/ql/test/extractor-smoke"
DB="$ROOT/.codeql-database/m1-luci"
rm -rf "$DB"
mkdir -p "$DB"

echo "== extract luci via extractor binary =="
FILELIST="$(mktemp)"
trap 'rm -f "$FILELIST"' EXIT
printf '%s\n' "$FIXTURE" >"$FILELIST"
EXTRACT_LOG="$(mktemp)"
trap 'rm -f "$FILELIST" "$EXTRACT_LOG"' EXIT

mkdir -p "$DB/diagnostics"
CODEQL_EXTRACTOR_UCODE_DIAGNOSTIC_DIR="$DB/diagnostics" \
	"$PACK/tools/linux64/extractor" extract \
	--file-list "$FILELIST" \
	--source-archive-dir "$DB/src" \
	--output-dir "$DB/trap" \
	2>&1 | tee "$EXTRACT_LOG"

if grep -q "No matching language found, skipping file" "$EXTRACT_LOG"; then
	echo "extractor skipped a file" >&2
	exit 1
fi

# Source archive must keep basename luci (not luci.uc).
if ! find "$DB/src" -type f -name luci | grep -q .; then
	echo "source archive has no file named luci" >&2
	find "$DB/src" -type f | head
	exit 1
fi
if find "$DB/src" -type f -name 'luci.uc' | grep -q .; then
	echo "source archive contains luci.uc" >&2
	exit 1
fi

echo "== codeql database init + index luci + finalize =="
# codeql-extractor.yml cannot declare an empty extension (CLI parse error).
# Index the extensionless plugin by path glob; extractor glob still requires basename luci.
rm -rf "$DB/db"
if ! codeql database init "$DB/db" \
	--language=ucode \
	--search-path="$PACK" \
	--source-root="$SRC"; then
	echo "codeql database init failed" >&2
	exit 1
fi
if ! codeql database index-files \
	--language=ucode \
	--include='**/luci' \
	--working-dir="$SRC" \
	"$DB/db"; then
	echo "codeql database index-files failed" >&2
	exit 1
fi
if ! codeql database finalize "$DB/db"; then
	echo "codeql database finalize failed" >&2
	exit 1
fi

echo "== SuccessfullyExtractedFiles =="
codeql query run "$ROOT/ql/src/diagnostics/SuccessfullyExtractedFiles.ql" \
	--database="$DB/db" \
	--search-path="$PACK" \
	--output="$DB/extracted.bqrs"
codeql bqrs decode --format=csv "$DB/extracted.bqrs" | tee "$DB/extracted.csv"
if [[ "$(codeql bqrs decode --format=csv "$DB/extracted.bqrs" | tail -n +2 | grep -c .)" -ne 1 ]]; then
	echo "expected count(SuccessfullyExtractedFiles) == 1" >&2
	exit 1
fi

echo "== ExtractionErrors empty =="
codeql query run "$ROOT/ql/src/diagnostics/ExtractionErrors.ql" \
	--database="$DB/db" \
	--search-path="$PACK" \
	--output="$DB/errors.bqrs"
ERRS="$(codeql bqrs decode --format=csv "$DB/errors.bqrs" | tail -n +2 | grep -c . || true)"
if [[ "$ERRS" -ne 0 ]]; then
	echo "expected empty ExtractionErrors" >&2
	codeql bqrs decode --format=csv "$DB/errors.bqrs"
	exit 1
fi

echo "== PrintLuciAst =="
codeql query run "$ROOT/ql/src/extractor-smoke/PrintLuciAst.ql" \
	--database="$DB/db" \
	--search-path="$PACK" \
	--output="$DB/ast.bqrs"
codeql bqrs decode --format=csv "$DB/ast.bqrs" | tee "$DB/ast.csv"
if [[ "$(codeql bqrs decode --format=csv "$DB/ast.bqrs" | tail -n +2 | grep -c .)" -lt 1 ]]; then
	echo "printAst/PrintLuciAst returned no luci nodes" >&2
	exit 1
fi

echo "M1 smoke passed"
