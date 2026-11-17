#!/usr/bin/env bash
# Caller supplies ROOT, DB, QLPATH and the exact selected absolute paths.
check_m4_extraction() {
  local diagnostic
  for diagnostic in SuccessfullyExtractedFiles ExtractionErrors; do
    codeql query run "$ROOT/ql/src/diagnostics/$diagnostic.ql" --database="$DB" --search-path="$QLPATH" --output="$DB/$diagnostic.bqrs" || return "$?"
    codeql bqrs decode --format=json --entities=url,string "$DB/$diagnostic.bqrs" > "$DB/$diagnostic.json" || return "$?"
  done
  python3 -B "$ROOT/scripts/m4-smoke-diagnostics.py" "$DB/SuccessfullyExtractedFiles.json" "$DB/ExtractionErrors.json" "$@"
}
