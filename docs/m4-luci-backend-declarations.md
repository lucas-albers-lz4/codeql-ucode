# LuCI backend source declarations (bounded table)

`ql/src/m4/LuciBackendDeclarations.ql` reports literal callback declarations in
one file, `usr/share/rpcd/ucode/luci`, relative to the CodeQL database source
root. It reports `source_declared_callback`, not registration, callability,
reachability, an authorization decision, a sink, taint, safety, or a typed
`backend_method` interchange record. The returned identifier is a source
shape, not a runtime registration proof. Existing models and interchange
contracts are unchanged.

The v1 shape is deliberately narrow: one direct program-level `const methods`
object and one direct program-level return object with a direct `luci: methods`
pair. All direct table entries must have unique identifier keys and object
values; all direct method-object and return-object keys must also be unique
identifier keys. Each method object has one direct `call` with a function
expression value. The query rejects the entire table when any such child is
unsupported or duplicated, including a duplicate nonfunction `call` overriding
a function. Callback body contents are not inspected. The conservative
ownership check permits the identifier `methods` only at the chosen declaration
and returned reference and rejects shorthand-property uses of that name: aliases,
direct mutations, nested declarations and otherwise harmless additional uses
are excluded. It is not a name resolver and
cannot prove absence of reflective mutation or dynamic runtime behavior.

Computed, quoted, shorthand and spread keys, indirect or arrow callbacks, other
returned bindings, dynamic assembly and alternate source layouts are unsupported.
An empty table, missing rows, or failed extraction is **unknown/error**, not an
empty or safe backend. A query alone cannot establish completeness: an acceptance
boundary must check successful extraction and errors, the exact source bytes,
and compare identity and location multiplicities with an independently reviewed
source oracle. Parser recovery, extraction limitations, and future syntax may
not be visible as a convenient unsupported-shape status. The query suppresses
rows for a file with an `ExtractionError` (including reported parse errors), but
this is not a promise that every possible extraction defect is diagnosed. In
particular do not interpret output for arbitrary unpinned or invalid input as
complete. No status row is emitted for unsupported input.

Columns, in order:

```
observation_kind,ubus_object,method,source_path,start_line,start_column,end_line,end_column
```

Coordinates are 1-based inclusive function-expression spans. The real fixture
is upstream `openwrt/luci@b2e0be4b46ec0fd43394c081fa7c50657af14011`, SHA-256
`6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e`.
`ql/test/backend-declarations-real-oracle.csv` is a separately transcribed
source review of its 21 names and spans; it is a producer regression oracle,
not an advertisement that a future consumer should blindly trust. A consumer
needs its own independently reviewed oracle and provenance checks.

## Reproduction

After following the README's grammar/bootstrap steps and placing CodeQL and
Rust on `PATH`:

```
M4_BACKEND_EVIDENCE_DIR="$TMPDIR/backend-declarations-evidence" \
  bash scripts/m4-backend-declarations-smoke.sh > "$TMPDIR/backend-declarations-smoke.log" 2>&1
```

The smoke creates a fresh database with a source root ending in
`ql/test/extractor-smoke`, indexes the pinned file at its exact relative path,
checks the actual routing decision before finalize, runs both extraction
diagnostics and the actual query, decodes BQRS, and checks all 21 reviewed
identities and spans with multiplicity. With the evidence variable it copies
the raw CSVs, BQRS, routing receipt and SHA-256 list. The shell log records the
commands and results. It then runs independently extracted synthetic programs
serially, including a basename-identical wrong path (with a ucode shebang so it
is actually routed), positive no-argument/request callbacks and unreturned
lookalikes, nested and wrong bindings, duplicate method/call/return keys,
unsupported forms, and alias/mutation controls. Every valid control requires its
actual file to appear in `SuccessfullyExtractedFiles` and zero extraction
errors. A malformed source instead requires a reported extraction error and no
table rows. It tests QL output, not a string-matched or mocked result.

`bash scripts/ci-ql-smoke.sh` discovers `m4-*-smoke.sh` automatically. Do not
run this focused smoke concurrently with the aggregate: they reuse fixed database
paths. The table is only a source denominator; any future policy comparison is
separate work and cannot turn an unmatched declaration into a denial or ACL
defect.

## Recorded real extraction

A fresh local run on CodeQL 2.27.4, producer base
`ae946190661eb221bc1f562fdba02088ef83de2d` plus this query (query SHA-256
`58d11ee8bf4f27db2dec4e34292d5155874f035bac8b98121c9ee8d85225a298`),
used the command above. The staged source was routed as
`rpcd_raw_mode_full_path` / `plain_route_selected`; `SuccessfullyExtractedFiles`
returned exactly the staged path and `ExtractionErrors` returned no rows. The
actual decoded table SHA-256 was
`245ad2dc1aedc9d4e0d41d83fcb0246a0990bcd70b5d0a35e1cb65100bfa8996`.
A separate pin-specific indentation scan of the source agreed with both the
transcribed oracle and all 21 decoded identities and spans; this is not a general
ucode parser. The table below is transcribed from that decoded output; each row also had
`source_declared_callback`, `luci`, and `usr/share/rpcd/ucode/luci` in the
corresponding fixed columns:

| Method | Function span |
|---|---|
| getVersion | 51:9–53:3 |
| getInitList | 58:9–72:3 |
| setInitAction | 77:9–95:3 |
| getUnixtime | 99:9–102:3 |
| setLocaltime | 107:9–116:3 |
| getTimezones | 120:9–133:3 |
| getLEDs | 137:9–161:3 |
| getUSBDevices | 165:9–192:3 |
| getConntrackHelpers | 196:9–220:3 |
| getFeatures | 224:9–336:3 |
| getSwconfigFeatures | 341:9–394:3 |
| getSwconfigPortState | 399:9–464:3 |
| setPassword | 469:9–476:3 |
| getBlockDevices | 480:9–527:3 |
| setBlockDetect | 531:9–533:3 |
| getMountPoints | 537:9–566:3 |
| getRealtimeStats | 571:9–602:3 |
| getConntrackList | 606:9–608:3 |
| getProcessList | 612:9–614:3 |
| getBuiltinEthernetPorts | 618:9–657:3 |
| getOdhcp6cStats | 661:9–682:3 |

Raw local BQRS, CSV, routing and hashes are in the execution's evidence
directory, not embedded as a fabricated result or a consumer acceptance claim.
Re-run the command to obtain evidence for a new execution and source root.
