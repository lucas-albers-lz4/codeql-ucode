# M4: Field / Element content from extracted AST

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Experimental call models can match unique same-file identifier and
member-property function declarations. The models do not resolve imported
`luci.sys` targets. Production `LocalTaint` and `RequestArgsExec` use Models.

## What compiles

- `TContent` includes field content for extracted `MemberExpression`
  properties, object pair keys, and shorthand properties. `Element` holds
  when a `SubscriptExpression` or a non-empty array is present.
- Smoke reports `Field[args]` on `luci`, `Field[field]` on `ssa_neg`,
  and `Element` on `luci`.
- No `Future` constructor. The grammar has no async/future nodes.

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
