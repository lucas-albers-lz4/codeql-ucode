# M4: Field / Element content from extracted AST

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
`viableSourceCallable` stays `none()`. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- `TContent` is inhabited from extracted AST: `Field` names from
  `MemberExpression` properties, object pair keys, and shorthand
  properties; `Element` when a `SubscriptExpression` or a non-empty
  array is present.
- Smoke reports `Field[args]` on `luci`, `Field[field]` on `ssa_neg`,
  and `Element` on `luci`. `storeStep` / `readStep` stay `none()`.
- No `Future` constructor. The grammar has no async/future nodes.

## Gaps (later PR)

- `storeStep` / `readStep` as production taint. Do not wire summary
  steps into `localFlowStep`.
- `ParameterNode` / argument-to-parameter flow (open ParameterPosition
  draft).
- MaD `sourceModel` / `sinkModel` interpretation (`SourceElement` /
  `SinkElement` are not in dataflow 1.1.6 `Public`).
- `codeql/threat-models` pack only with lockfile discipline.
