# M4: `Call.getArgument` from extracted arguments children

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Experimental call models can match unique same-file identifier and
member-property function declarations. The models do not resolve imported
`luci.sys` targets. Production `LocalTaint` and `RequestArgsExec` use Models.

## What compiles

- Public `Call.getArgument` is inhabited from TreeSitter
  `call_expression` `arguments` children that are already `TExpr`
  (identifiers, strings, members, nested calls, binary expressions).
- The original argument smoke reports `0:ssa_pos_src` on `ssa_pos` and
  `0:pkg` / `1:r` on `luci`. Extracted arguments can have
  `ArgumentPosition`s. An argument with a CFG node in the call scope can
  also have an `ArgumentExpr` and an `ArgumentNode`.
- `getArguments()` stays `none()` (`Arguments` is not `Expr`).
  `getIdentifier()` returns extracted identifier callees. Named formals
  with CFG nodes have `ParameterNode`s. See
  [parameter nodes](m4-parameter-node.md).

## Limits and related models

- Children that are not `TExpr` (template strings, numbers, arrays,
  objects, spreads, arrows, `this`) have no `getArgument` result.
  Do not widen `TExpr` here. That change affects CFG membership.
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
