# M4: ParameterPosition from extracted formals

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
`viableSourceCallable` stays `none()`. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- `TParameterPosition` is inhabited from extracted `FormalParameters`
  children (`identifier` or `rest_element`) and from a bare arrow
  `parameter` field (`x => ...`).
- Smoke reports `pos:name` on `luci` and `ssa_pos`. Position `1` is
  extractable (`(_, n) =>` in the luci plugin).
- `ParameterNode` stays uninhabited. `parameterMatch` still does not
  hold: public `Call.getArgument` is `none()` on the generated
  `CallExpression` wrapper, so `ArgumentPosition` stays empty.

## Gaps (later PR)

- `ParameterNode` / argument-to-parameter flow. Formals are not SSA
  source variables; `ParameterNodes` is still empty.
- Content encoding (`Field` / `Element` / `Future`). `TContent` is
  still `TFieldContent` with `none()`. Do not add `storeStep` /
  `readStep` as production taint.
- MaD `sourceModel` / `sinkModel` interpretation (`SourceElement` /
  `SinkElement` are not in dataflow 1.1.6 `Public`).
- `codeql/threat-models` pack only with lockfile discipline.
- Do not wire summary steps into `localFlowStep` / production taint.
