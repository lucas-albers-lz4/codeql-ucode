# M4: FlowSummary / Concepts compile slice

Typecheck only. Not production taint and not `path_found`.
Unique same-file identifier FunctionDeclarations may resolve;
imported `luci.sys` stays unresolved. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- `FlowSummaryImpl` implements `codeql/dataflow` 1.1.6 `InputSig` with
  string-keyed `SummarizedCallableBase` (Python-style). Generator leftovers
  (`Function`, `CallExprBase`, `Resolvable`, `Addressable`, crate paths,
  `Stdlib`) are gone.
- `SummarizedCallable` and MaD `summaryModel` rows typecheck (compile
  smoke still imports ModelsAsData). Identifier `getACall` is a separate
  slice ([m4-get-a-call.md](m4-get-a-call.md)): identifier callees whose
  name matches a Frameworks summary key are returned; member callees
  stay `none()`.
- `FlowSource` / `FlowSink` `Range` classes extend `DataFlow::Node`.
- `Frameworks.qll` contributes identifier-keyed summaries (`system`,
  `popen`, `shellquote`) with `propagatesFlow` still `none()`.
- `Concepts.qll` typechecks with `codeql/threat-models`. No ucode
  `ThreatModelSource::Range` models yet, so `ActiveThreatModelSource` stays
  uninhabited.

## Gaps (later PR)

- `SourceElement` / `SinkElement` are not in dataflow 1.1.6 `Public`.
  MaD `sourceModel` / `sinkModel` rows are not interpreted into nodes.
- Do not wire summary steps into `localFlowStep` / production taint.
