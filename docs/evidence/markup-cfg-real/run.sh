#!/bin/bash
set -euo pipefail
# Run from producer root, after building its pack. Arguments are absolute paths.
if [ "$#" -lt 5 ] || [ "$#" -gt 6 ] || { [ "$#" -eq 6 ] && [ "$6" != "--call-bundle" ]; }; then echo 'usage: run.sh CODEQL STAGE LUCI CONSUMER OUT [--call-bundle]' >&2; exit 2; fi
CODEQL=$1 STAGE=$2 LUCI=$3 CONSUMER=$4 OUT=$5
EVIDENCE="$PWD/docs/evidence/markup-cfg-real"
[ ! -e "$OUT" ] || { echo 'output already exists' >&2; exit 1; }
mkdir -p "$OUT"
for q in measurement measurement-callable measurement-witness; do
  [ ! -e "ql/src/$q.ql" ] || { echo "query already exists: ql/src/$q.ql" >&2; exit 1; }
done
trap 'rm -f ql/src/measurement.ql ql/src/measurement-callable.ql ql/src/measurement-witness.ql' EXIT
for q in measurement measurement-callable measurement-witness; do cp "$EVIDENCE/$q.ql" "ql/src/$q.ql"; done
# Do not overwrite a pre-existing database. The command log and every output are retained.
run_db() {
  local root=$1 db=$2
  "$CODEQL" database init "$db" --language=ucode --search-path="$PWD/extractor-pack" --source-root="$root"
  CODEQL_UCODE_STAGED_ROOT="$root" "$CODEQL" database index-files "$db" --language=ucode '--include=**/*.uc' '--include=**/*.ut' --working-dir="$root"
  cp "$db/trap/ucode/routing.json" "$OUT/$(basename "$db")-routing.json"
  "$CODEQL" database finalize "$db"
}
query() {
  local db=$1 q=$2 name=$3 format=$4
  "$CODEQL" query run "ql/src/$q.ql" --database="$db" --search-path="$PWD/extractor-pack" --output="$OUT/$name.bqrs" --threads=1 --ram=2048
  if [ "$format" = json ]; then
    "$CODEQL" bqrs decode --format=json --entities=url,string "$OUT/$name.bqrs" > "$OUT/$name.json"
  else
    "$CODEQL" bqrs decode --format=csv "$OUT/$name.bqrs" > "$OUT/$name.csv"
  fi
}
run_db "$STAGE" "$OUT/real-db"
cp "$OUT/real-db-routing.json" "$OUT/markup-measure-routing.json"
for q in measurement measurement-callable markup-creation-nodes-test markup-creation-edges-test; do query "$OUT/real-db" "$q" "markup-measure-$q" csv; done
query "$OUT/real-db" measurement-witness markup-measure-witness csv
for q in SuccessfullyExtractedFiles ExtractionErrors; do query "$OUT/real-db" "diagnostics/$q" "markup-measure-$q" json; done
python3 "$CONSUMER/evidence/markup-profile-0a6612f/validate.py" --source "$LUCI" --stage "$STAGE" --receipt "$OUT/markup-measure-routing.json" --extracted "$OUT/markup-measure-SuccessfullyExtractedFiles.json" --errors "$OUT/markup-measure-ExtractionErrors.json"
run_db "$EVIDENCE/controls" "$OUT/controls-db"
for q in measurement measurement-callable; do query "$OUT/controls-db" "$q" "markup-measure-controls2-$q" csv; done
for q in SuccessfullyExtractedFiles ExtractionErrors; do query "$OUT/controls-db" "diagnostics/$q" "markup-measure-controls2-$q" csv; done
python3 "$EVIDENCE/check.py" "$OUT" "$STAGE" "$EVIDENCE/controls" "${@:6}"
