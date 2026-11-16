# M4: MaD `encodeContent` Field / Element tokens

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Experimental call models can match unique same-file identifier and
member-property function declarations. The models do not resolve imported
`luci.sys` targets. Production `LocalTaint` and `RequestArgsExec` use Models.

## What compiles

- `FlowSummaryImpl` `encodeContent` maps inhabited `TContent` to MaD
  tokens: `Field[name]` for extracted field names, `Element` for
  subscript / array content.
- `Future` stays `none()`. The grammar has no async/future nodes.
- Smoke reports `Field[args]` on `luci`, `Field[field]` on `ssa_neg`,
  and `Element` on `luci`. The encoding smoke does not assess call matching.
- `getACall` matches identifier callees to summary keys by name. This
  relation does not establish a runtime target or add summary steps to
  `localFlowStep`. Member callees have no result. See
  [identifier call matching](m4-get-a-call.md).

## Limits and related models

- `storeStep` / `readStep` as production taint. Extractor-smoke
  inhabitation is in [m4-store-read.md](m4-store-read.md). Do not wire
  summary steps into `localFlowStep`.
- Named formals with CFG nodes have `ParameterNode`s. The separate
  position match does not resolve calls. See
  [parameter nodes](m4-parameter-node.md).
- MaD `sourceModel` / `sinkModel` interpretation (`SourceElement` /
  `SinkElement` are not in dataflow 1.1.6 `Public`).
- `codeql/threat-models` pack only with lockfile discipline.
