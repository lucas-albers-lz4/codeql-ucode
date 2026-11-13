# M4: FlowSummary / Concepts compile slice

Typecheck only. Not production taint and not `path_found`.
`viableSourceCallable` stays `none()`. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- `FlowSummaryImpl` implements `codeql/dataflow` 1.1.6 `InputSig` with
  string-keyed `SummarizedCallableBase` (Python-style). Generator leftovers
  (`Function`, `CallExprBase`, `Resolvable`, `Addressable`, crate paths,
  `Stdlib`) are gone.
- `SummarizedCallable` and MaD `summaryModel` rows typecheck.
  `getACall` is `none()`, so summaries do not attach to source calls.
- `FlowSource` / `FlowSink` `Range` classes extend `DataFlow::Node`.
- `Frameworks.qll` is a valid empty module.
- `Concepts.qll` typechecks with `codeql/threat-models`. No ucode
  `ThreatModelSource::Range` models yet, so `ActiveThreatModelSource` stays
  uninhabited.

## Gaps (later PR)

- `SourceElement` / `SinkElement` are not in dataflow 1.1.6 `Public`.
  MaD `sourceModel` / `sinkModel` rows are not interpreted into nodes.
- Do not wire summary steps into `localFlowStep` / production taint.
