# M4: `Call.getIdentifier` from extracted function identifiers

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Unique same-file identifier FunctionDeclarations may resolve;
imported `luci.sys` stays unresolved. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- Public `Call.getIdentifier` is inhabited from TreeSitter
  `call_expression` `function` when that field is already an identifier
  (`system(...)`, `popen(...)`).
- Smoke reports `system` on `ssa_pos` and `popen` / `shellquote` on
  `luci`. Member callees (`fd.read(...)`) have no identifier.
- `getArguments()` stays `none()` (`Arguments` is not `Expr`).
  `ParameterNode` stays uninhabited. `ArgumentExpr` stays `none()`.

## Gaps (later PR)

- Callees that are not identifiers (members, subscripts, parenthesized
  expressions, nested calls) have no `getIdentifier` result. Do not walk
  `getAFieldOrChild`: that would treat a member object or property as
  the callee name.
- `getArguments()` cannot return `Expr`; the extracted node is
  `Arguments`. Do not change that signature here.
- `ParameterNode` / argument-to-parameter flow (open store/read and
  formals drafts).
- MaD `encodeContent` (`Field` / `Element` / `Future` tokens) lives in
  `FlowSummaryImpl` (open FlowSummary/Concepts draft).
- `storeStep` / `readStep` as production taint. Do not wire summary
  steps into `localFlowStep`.
- MaD `sourceModel` / `sinkModel` interpretation (`SourceElement` /
  `SinkElement` are not in dataflow 1.1.6 `Public`).
- `codeql/threat-models` pack only with lockfile discipline.
