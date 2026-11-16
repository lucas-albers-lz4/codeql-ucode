# M4: `Call.getIdentifier` from extracted function identifiers

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Experimental call models can match unique same-file identifier and
member-property function declarations. The models do not resolve imported
`luci.sys` targets. Production `LocalTaint` and `RequestArgsExec` use Models.

## What compiles

- Public `Call.getIdentifier` is inhabited from TreeSitter
  `call_expression` `function` when that field is already an identifier
  (`system(...)`, `popen(...)`).
- Smoke reports `system` on `ssa_pos` and `popen` / `shellquote` on
  `luci`. Member callees (`fd.read(...)`) have no identifier.
- `getArguments()` stays `none()` (`Arguments` is not `Expr`). Extracted
  arguments can have an `ArgumentExpr` when they have a CFG node in the
  call scope. Named formals with CFG nodes have `ParameterNode`s. See
  [parameter nodes](m4-parameter-node.md).

## Limits and related models

- Callees that are not identifiers (members, subscripts, parenthesized
  expressions, nested calls) have no `getIdentifier` result. Do not walk
  `getAFieldOrChild`. That approach treats a member object or property as
  the callee name.
- `getArguments()` cannot return `Expr`. The extracted node is
  `Arguments`. Do not change that signature here.
- Same-file call `jumpStep` has separate controls. See
  [identifier call jumps](m4-simple-call-jump.md) and
  [member call jumps](m4-member-call-jump.md).
- MaD `encodeContent` maps extracted field and element content to
  tokens. See [content encoding](m4-encode-content.md).
- `storeStep` / `readStep` as production taint. Do not wire summary
  steps into `localFlowStep`.
- MaD `sourceModel` / `sinkModel` interpretation (`SourceElement` /
  `SinkElement` are not in dataflow 1.1.6 `Public`).
- `codeql/threat-models` pack only with lockfile discipline.
