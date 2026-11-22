# Direct-copy receiver observation measurement

At producer `d3981986ac685d6fcbb78a3b369aa4ed526c1e4b`, the existing source-observation query `FsReceiverProvenance.ql` emitted 18 rows in a fresh extraction: 14 for pinned LuCI RPC source, three for pinned `sys.uc`, and one for the synthetic control. A local experimental union adds the exact bounded direct-copy relation from `ReceiverDirectCopy.ql`, projecting to the same six columns. It emitted 23 rows: all 18 baseline raw rows were retained and the five new rows were the independently specified synthetic direct-copy witnesses. The two real files' 17-row multiset did not change. `check.py` checks the complete unchanged raw rows, the added rows' file identities, coordinates and scalar fields, exact call-site control inventory, source hashes, selected files, routing and error count. It also exercises label, URI-scheme and added-coordinate mutations. Labels for added entities are retained but not independently specified.

The copy branch observes possible reaching definitions, and does not apply all the direct-origin branch's escape restrictions. Neither branch establishes a runtime target, resource identity, safety or security coverage. This experiment does not change a production query, extractor, dataflow, or model. The existing `RequestArgsExec.ql` output is also retained (seven rows); it examines data reaching inputs to `popen` or `system`, and the later receiver relation is not a sound replacement for its sink condition. No claim of a production-query change follows. This result is bounded to the selected files, extractor, and experiment.

## Inputs and run

The two real fixtures are from LuCI `b2e0be4b46ec0fd43394c081fa7c50657af14011`: `usr/share/rpcd/ucode/luci`, SHA-256 `6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e`, and `usr/share/ucode/luci/sys.uc`, `0380fba5d843a8950bab0ef70982cb40ab8f475e8d267c873e4199a736b55656`. The independent controls are `ql/test/receiver-provenance/direct-copy-controls.uc`, SHA-256 `a08377a54e42b09af7ff78557100bbd2031e7dc79ccfaf90134d5701554ebaf1`. All three are retained in this repository. The 25-call expected inventory and five full direct-copy witnesses are specified in `scripts/m4-receiver-direct-copy-smoke.py`.

The local run used CodeQL 2.27.4 and a reused macOS extractor pack built at producer `e37b1d298999b43deacc1f0cc1f693e6fe69ff05`, with binary SHA-256 `35aeb3a59305c7fb21b9ead30d658add5d255645f3f73efc877f5363abf242a8`, grammar `4a243af329fae2f4ff01e0fc80133cbab8314600` and github/codeql extractor `ce29d8a59af0d25517c622469db17aad826b8d7f`. The grammar build changed its dev dependency from 0.27.1 to =0.26.8. Tracked extractor source, build script, schema, generated TreeSitter library and lockfile have no diff between e37b1d2 and d398198; this is a reused pack, not a rebuild or a reproducible-build claim. Database initialization, indexing, finalization and all queries succeeded. Routing selected exactly three files, zero exclusions; successfully-extracted diagnostics contained the same three identities and extraction errors were empty.

`*.json` are decoded CodeQL output with the original staged absolute source prefix consistently replaced by `/STAGED_SOURCE` in entity URIs and labels; `routing.json` has the same replacement in source paths. No other values were intentionally changed. They are normalized snapshots, not raw CodeQL files; `SHA256SUMS` pins their retained bytes and query sources. Original unnormalized BQRS and logs were retained locally for independent audit, but are not included in this compact package. Initial attempts are invalid evidence: the first could not resolve the extractor through a symlinked search path, and the second omitted the staged-root setting and excluded extensionless `luci`; a separate initial baseline compile had a syntax error. The successful extraction was fresh and used `CODEQL_UCODE_STAGED_ROOT` to route the RPC file. A later comparator typo failed before comparison and was corrected. None of these failed attempts is used in the result.

## Verify and reproduce

From the repository root, run `python3 evidence/receiver-direct-copy-20261122/check.py` and `shasum -a 256 -c evidence/receiver-direct-copy-20261122/SHA256SUMS`. These validate the retained snapshots; they do not run a fresh extraction.

For a fresh run, use CodeQL 2.27.4 and a compatible built extractor pack, and set `CODEQL` to the CLI executable and `PACK` to its actual extractor-pack directory. Create a new empty `STAGE` and `OUT` directory and choose a nonexistent `DB` destination. Copy the three fixture bytes under `STAGE/usr/share/rpcd/ucode/luci`, `STAGE/usr/share/ucode/luci/sys.uc`, and `STAGE/controls/direct-copy-controls.uc`, preserving their names. Verify the three hashes above. From the repo root:

```sh
"$CODEQL" pack ci ql/lib
"$CODEQL" pack ci ql/src
SEARCH="$PACK:$PWD/ql/lib:$PWD/ql/src"
"$CODEQL" database init "$DB" --language=ucode --search-path="$SEARCH" --source-root="$STAGE"
CODEQL_UCODE_STAGED_ROOT="$STAGE" "$CODEQL" database index-files "$DB" --language=ucode '--include=**/*.uc' '--include=**/luci' --working-dir="$STAGE"
cp "$DB/trap/ucode/routing.json" "$OUT/routing.json"
"$CODEQL" database finalize "$DB"
```

Set `OUT` to a separate empty directory. Retain and inspect routing and run `ql/src/diagnostics/SuccessfullyExtractedFiles.ql` and `ql/src/diagnostics/ExtractionErrors.ql` before interpreting results. Query from the repository root with these options, once for each query path, naming separate output files:

```sh
"$CODEQL" query run "$QUERY" --database="$DB" --search-path="$SEARCH" --output="$OUT/$NAME.bqrs" --threads=1 --ram=2048 --no-default-compilation-cache --no-use-precompiled
"$CODEQL" bqrs decode --format=json --entities=url,string "$OUT/$NAME.bqrs" > "$OUT/$NAME.json"
```

The executed baseline was `ql/src/m4/FsReceiverProvenance.ql`; the experiment was the retained `ReceiverMeasureUnion.ql` copied unchanged into a newly created unique `.ql` file under `ql/src/m4` (CodeQL requires it in the query pack). Remove only that temporary file after the run. Also run `ql/src/m4/ReceiverDirectCopy.ql`, `ql/src/m4/ReceiverDirectCopyCallInventory.ql` and `ql/src/m4/RequestArgsExec.ql` for the other retained observations. Normalize only the staged source prefix in decoded entity URIs and labels and in routing source paths, then compare full row multisets and diagnostics against the snapshots. The checker tests the snapshots, not arbitrary newly generated output. Expected source SHA-256: baseline query `6d6520289ce75685969cb4e405e771cab032ae05807136400493f5b717030032`; union query `4884fbf08543ee8a0b3aca1675d1781290b6e15abe5163e8c4cf85769a2b78f8`.
