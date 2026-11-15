# setBlockDetect source observation table

`SetBlockDetectEffectTable.ql` emits a CSV/BQRS table using the columns
`observation_kind`, `method`, `sink_kind`, `command`, `source_path`,
`start_line`, `start_column`, `end_line`, and `end_column`. A row records a
direct identifier `system` call with exactly one argument, the literal
`/sbin/block detect > /etc/config/fstab`, syntactically inside a
`setBlockDetect.call` function. The `BuiltinSystemCall` model excludes visible
bindings named `system`, including imports, parameters and lexical declarations,
using the shared syntactic model. The source path is relative to the database
source root; coordinates cover the call expression. The pinned LuCI copy in
`ql/test/extractor-smoke` yields the call on line 532.

The row is a source observation, not a `handler_effect`: it does not establish
registration, reachability, execution, dataflow or authorization. The model
approximates lexical binding in source order; it does not resolve global
reassignment or builtin aliases. Nested function bodies are also syntactically
contained. Nonliteral commands, wrapped or member callees and other unsupported
shapes are outside this table; absence of a row is not proof that no effect
exists. This query does not read grants or assert `path_found`, `no_path`, or
an authorization violation.

The [opt-in typed exporter](interchange.md#opt-in-typed-setblockdetect-source-observation-v1)
validates the pinned source, supported lock and diagnostic shapes, then maps
the single supported observation to an unassessed source-only `handler_effect`
with fixed profile, entrypoint binding, conditions and uncertainty. The lock's
raw bytes determine the corpus revision. Neither supplied inputs nor that
mapping authenticate query execution or freshness. A downstream OpenWrt driver
must establish its own provenance and perform policy assessment; these are not
implemented by the exporter. The focused smoke checks the
pinned file hash, extraction errors, table columns, exact values and locations,
plus synthetic positive and negative controls, including sibling scopes,
shadowed calls, and a `system` formal parameter whose literal call must stay
excluded.

## Reproduction and provenance

The following local evidence used CodeQL CLI 2.27.4 (CLI SHA
`7eb0047c90fffaeb822564a0ac56d585dc871f30`), ucode base commit
`08e2784de4850f55685f05a7e1d47f6c72a838d3`, and **uncommitted** restored
query SHA-256 `b1c56c68bd96e537e5665d526060f3a09031fdf951d878fba992a5b6db9d338a`.
At the time of that local reproduction there was no new producer commit; the
base SHA is not a claim that this query existed in that commit. The LuCI fixture
is the byte copy of revision `b2e0be4b46ec0fd43394c081fa7c50657af14011` with SHA-256
`6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e`.
The focused reproduction CSV SHA-256 was
`add11a618a26fad1c83c3d3ec50b0d2e32bcac4640071b4b217d8bde8bc6f1ff`.
That CSV uses the repository-layout path and is **not** accepted by the
consumer's installed-relative path requirement. A separate fresh CodeQL run,
using `ql/test/extractor-smoke` as its source root, produced the consumer input
with path `usr/share/rpcd/ucode/luci` and CSV SHA-256
`9d9a1a7178e7f5fbd3cb772122fe172354004fac09ce00e91647d6b35ba9d0a0`.
These digests identify these runs; a CSV itself does not authenticate its origin.

After the README bootstrap, a fresh single-file output can be reproduced from
this repository root (use a disposable empty directory for `RUN`):

```bash
RUN=/path/to/disposable/run
mkdir -p "$RUN/src/modules/luci-base/root/usr/share/rpcd/ucode"
cp ql/test/extractor-smoke/usr/share/rpcd/ucode/luci \
  "$RUN/src/modules/luci-base/root/usr/share/rpcd/ucode/luci"
sha256sum "$RUN/src/modules/luci-base/root/usr/share/rpcd/ucode/luci" \
  ql/src/m4/SetBlockDetectEffectTable.ql
source scripts/ql-smoke-pack-install.sh # Set ROOT for the shared installer.
ROOT="$PWD"; install_smoke_packs
codeql database init "$RUN/db" --language=ucode --search-path="$PWD/extractor-pack" --source-root="$RUN/src"
codeql database index-files --language=ucode --include='**/rpcd/ucode/luci' --working-dir="$RUN/src" "$RUN/db"
codeql database finalize "$RUN/db"
QLPATH="$PWD/extractor-pack:$PWD/ql/lib:$PWD/ql/src"
for entry in 'diagnostics/SuccessfullyExtractedFiles.ql extracted' \
  'diagnostics/ExtractionErrors.ql errors' 'm4/SetBlockDetectEffectTable.ql effects'; do
  read -r query output <<< "$entry"
  codeql query run "$PWD/ql/src/$query" --database="$RUN/db" --search-path="$QLPATH" --output="$RUN/$output.bqrs"
  codeql bqrs decode --format=csv "$RUN/$output.bqrs" > "$RUN/$output.csv"
done
sha256sum "$RUN/effects.csv"
```

Inspect the diagnostics: this run extracted exactly one file and had no
extraction errors. Its one result has source path
`modules/luci-base/root/usr/share/rpcd/ucode/luci` and coordinates
`532:21–532:68`. This repository-layout output is not suitable for the current
consumer. To generate its installed-relative input, use a separate empty `RUN`
and repeat the database and query commands above with `ROOT="$PWD"`, replacing
`--source-root="$RUN/src"` and `--working-dir="$RUN/src"` with
`--source-root="$ROOT/ql/test/extractor-smoke"` and
`--working-dir="$ROOT/ql/test/extractor-smoke"`, respectively, and retain the
single-file `--include` pattern. Confirm the sole output path is
`usr/share/rpcd/ucode/luci` and that extraction diagnostics report one file and
zero errors before passing the CSV and that same source root to the adapter.
The multi-file focused smoke uses other source roots and is likewise unsuitable
for direct import.
Run `bash scripts/m4-setblockdetect-effect-table-smoke.sh` and then
`bash scripts/ci-ql-smoke.sh` serially; do not run database smokes concurrently.

For the local test-first check, the new fixture and unchanged smoke assertion
were run against the restored query in a scratch pack with `Models.qll` from
`08e2784^`: the shadowed calls at lines 5 and 12 appeared incorrectly and the
assertion rejected the result. With current `Models.qll`, those calls disappear
and the sibling builtin at line 8 remains. As a count-preserving identity
control, an actual scratch query was changed to substitute `otherMethod` for
the positive fixture: five rows still resulted, but the unchanged location
assertion rejected the wrong source and passed again with the real results.
A second scratch mutation broadened the lexical scope of declarations: the
builtin sibling call at line 8 and the later builtin at line 14 disappeared;
the same assertion rejected that output and passed after restoring real output.
The serial local aggregate exited 0 and visited all 33 expected M4 script markers
exactly once, including this smoke. The successful CI `cargo-test` job is recorded
in [run 43652449266](https://github.com/lucas-albers-lz4/codeql-ucode/actions/runs/43652449266),
and the successful `m3-m4-smoke` job in
[run 43652449286](https://github.com/lucas-albers-lz4/codeql-ucode/actions/runs/43652449286).
Both runs have head SHA `10644b70c5dbd2dd5b90f5d5dfcf82a1fafd6965`; this is the
pre-change PR head, not a claim that these runs exercised the later formal
parameter fixture. The local Python unit-test result is not claimed here.

For the new formal-parameter control, a scratch-pack mutant removing
`not systemFormalInBody(this)` produced six rows and the unchanged smoke
assertion failed on the extra call at `negative-formal-parameter`, `4:7–4:54`.
With the real model, the smoke passed with exactly the original five source
sites. The mutant and clean BQRS/CSV outputs plus assertion logs are preserved
under `/root/.hermes/profiles/work/cache/scratch/pr79-formal-red/artifacts/`
and `/root/.hermes/profiles/work/cache/scratch/pr79-formal-green/`.
