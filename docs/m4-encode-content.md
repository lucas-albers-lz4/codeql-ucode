# M4: MaD `encodeContent` Field / Element tokens

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
`viableSourceCallable` stays `none()`. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- `FlowSummaryImpl` `encodeContent` maps inhabited `TContent` to MaD
  tokens: `Field[name]` for extracted field names, `Element` for
  subscript / array content.
- `Future` stays `none()`. The grammar has no async/future nodes.
- Smoke reports `Field[args]` on `luci`, `Field[field]` on `ssa_neg`,
  and `Element` on `luci`. `getACall` stays `none()`, so summaries do
  not attach to source calls.

## Gaps (later PR)

- `storeStep` / `readStep` as production taint. Extractor-smoke
  inhabitation is in [m4-store-read.md](m4-store-read.md). Do not wire
  summary steps into `localFlowStep`.
- `ParameterNode` / argument-to-parameter flow.
- MaD `sourceModel` / `sinkModel` interpretation (`SourceElement` /
  `SinkElement` are not in dataflow 1.1.6 `Public`).
- `codeql/threat-models` pack only with lockfile discipline.
