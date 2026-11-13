# M4: `Call.getArgument` from extracted arguments children

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Unique same-file identifier and member-property FunctionDeclarations may resolve;
imported `luci.sys` stays unresolved. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- Public `Call.getArgument` is inhabited from TreeSitter
  `call_expression` `arguments` children that are already `TExpr`
  (identifiers, strings, members, nested calls, binary expressions).
- Smoke reports `0:ssa_pos_src` on `ssa_pos` and `0:pkg` / `1:r` on
  `luci`. `ArgumentPosition` is therefore inhabited on main's
  `DataFlowDispatch` without editing that file.
- `getArguments()` stays `none()` (`Arguments` is not `Expr`).
  `getIdentifier()` stays `none()`. `ParameterNode` stays uninhabited.
  `ArgumentExpr` stays `none()`.

## Gaps (later PR)

- Children that are not `TExpr` (template strings, numbers, arrays,
  objects, spreads, arrows, `this`) have no `getArgument` result.
  Do not widen `TExpr` here: that would change CFG membership.
- `ParameterNode` / argument-to-parameter flow (open ParameterPosition
  draft).
- MaD `encodeContent` (`Field` / `Element` / `Future` tokens) lives in
  `FlowSummaryImpl` (open FlowSummary/Concepts draft).
- `storeStep` / `readStep` as production taint. Do not wire summary
  steps into `localFlowStep`.
- MaD `sourceModel` / `sinkModel` interpretation (`SourceElement` /
  `SinkElement` are not in dataflow 1.1.6 `Public`).
- `codeql/threat-models` pack only with lockfile discipline.
