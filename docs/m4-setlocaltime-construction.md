# setLocaltime source-construction table (v1)

`ql/src/m4/SetLocaltimeConstructionTable.ql` is an additive **source-shape
observation**. It does not modify production taint, resolve runtime call
targets, prove builtin behavior, remove a candidate, establish registration or
execution, assess authorization, or assert a sanitizer, `no_path`, or security
coverage. An absent row, extraction error, unsupported form, or other failure
is **inconclusive**, not a safe result.

The query requires the database-relative path `usr/share/rpcd/ucode/luci`, no
extraction error, a direct program-level `const methods` returned as
`{ luci: methods }`, unique plain keys, the selected direct
`setLocaltime.call`, and the supported exact callback statement/argument
structure. It requires the pinned `args` metadata, a single `request` formal,
`let t = localtime(request.args.localtime)`, direct `if (t)`, the complete
formatter passed as the sole argument of the date `system` call, the fixed
sysfixtime sibling, and the direct result return. Its ordered direct field
expressions are `t.year`, `t.mon`, `t.mday`, `t.hour`, `t.min`, `t.sec`. The
complete, plain, escape-free literal must be exactly:

```text
date -s "%04d-%02d-%02d %02d:%02d:%02d" >/dev/null
```

Each `system`, `sprintf`, and `localtime` identifier occurrence in the file
must be a direct nonoptional call; shorthand uses are excluded. This is a
conservative whole-file source subset: unrelated, later, or out-of-scope
competitors also prevent observation. It is **not** a scope engine or proof of
genuine builtin identity. Reflective writes such as
`global['sprintf'] = ...`, imported side effects, and embedding/runtime
mutation can change behavior while the source shape still matches. In
particular, even the included reflective control is conditional/unknown, not
safe. Escaped equivalent literals, wrappers, alternate statements or binding
shapes are unsupported, not unsafe.

## Transport

Decode the result as UTF-8 CSV with `codeql bqrs decode --format=csv`. The
41 columns, in order, are:

```text
observation_kind,ubus_object,method,source_path,local_name,format_value,callback_start_line,callback_start_column,callback_end_line,callback_end_column,initializer_start_line,initializer_start_column,initializer_end_line,initializer_end_column,input_start_line,input_start_column,input_end_line,input_end_column,guard_start_line,guard_start_column,guard_end_line,guard_end_column,formatter_start_line,formatter_start_column,formatter_end_line,formatter_end_column,format_start_line,format_start_column,format_end_line,format_end_column,sink_start_line,sink_start_column,sink_end_line,sink_end_column,slot_index,conversion,field_name,field_start_line,field_start_column,field_end_line,field_end_column
```

The common kind is `setlocaltime_complete_decimal_datetime_source_v1`, object
`luci`, method `setLocaltime`, and local `t`. Each construction has six rows,
indices 1 through 6, respectively `%04d/year`, `%02d/mon`, `%02d/mday`,
`%02d/hour`, `%02d/min`, `%02d/sec`. These are **one construction**, not six
calls or effects. Coordinates are 1-based inclusive source-byte columns;
tabs count as one. The guard is the inner identifier. CSV order is not
semantic: compare complete rows as a multiset, preserving duplicates and all
span endpoints, then sort by slot for display. All common fields must agree.
No policy or safety authority fields are carried.

The query enforces the path and diagnostics, but does **not** authenticate
source bytes, establish freshness, or verify execution provenance. Consumers
must independently check routing, successful extraction, zero errors, source
bytes and their own pinned source-first identity/multiplicity oracle before
using the result. Do not substitute a producer-selected oracle for that check.
The pinned fixture in this repository has SHA-256
`6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e`.

## Reproduction and tests

After the repository's normal grammar/extractor bootstrap, with `codeql` on
`PATH`, run:

```sh
bash scripts/m4-setlocaltime-construction-smoke.sh
```

The script creates serial exclusive temporary databases. It checks the pinned
source's routing and diagnostics, the complete 41-column output against a
separately transcribed source oracle, and the exact unchanged production
source/sink candidate in both production queries. It executes count-preserving
wrong-sink and wrong-field query mutations against the same oracle. A second
batch exercises a minimal fixture, comments, reflective mutation, six `%s`
positions, reordered and rebound values, malformed source, wrong paths,
formatter variations, and whole-file shadowing/binding controls for each
callee. It checks actual routing and per-file extraction diagnostics. Isolated
real-query mutants separately exercise the extraction-error, format,
field-order and `sprintf` lexical guards. Other individual guard mutations
are not claimed as exhaustively killed. Statement-shape restrictions can make
some occurrence checks redundant for particular controls.

Set `M4_SETLOCALTIME_EVIDENCE_DIR` to copy the real source table, diagnostics,
routing, candidate entity decodes, and the two wrong-identity query outputs
from a successful focused run. The control database and other mutation outputs
are temporary; a successful test log is not an attested handoff. The copied
extractor binary or cached query plans may be reused, as determined by the
local environment. Run the consumer independently, with its own oracle and
context pins; producer tests alone are not a consumer acceptance run.
