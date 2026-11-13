# M4: `jumpStep` from same-file identifier `Call.getArgument` into `ParameterNode`

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
`viableSourceCallable` stays `none()`. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- `simpleIdentifierCall` joins a `Call.getIdentifier` name to a
  same-file `function` declaration whose body is the callee `CfgScope`.
  That is the Models `sameFileCall` evidence already on main, not a
  call graph.
- `jumpStep` takes `Call.getArgument` `ArgumentNode`s into that
  callee's `ParameterNode` at the matching `ParameterPosition`.
  `#29` `arg-param` position match without a same-file identifier
  declaration does not jump (`system(...)` on `ssa_pos` does not
  enter `formal_order`).
- Smoke reports `0:s` from `shellquote` and `0:pkg` from
  `callPackageVersionCheck` on `luci`. `ssa_pos` has ParameterNodes
  and `arg-param` rows, but no jumpStep rows.
- `Call.getArguments()` stays `none()`. Summary steps stay out of
  `localFlowStep`. Public `localFlowStep` does not include `jumpStep`.
  Body continuation from that `ParameterNode` is `parameterToSsaDef`
  (see `docs/m4-jump-local.md`).

## Gaps (later PR)

- Function expressions (`function(request) { ... }`) and arrows are
  not declarations, so they are not simple-call targets.
- Member, subscript, parenthesized, and nested-call callees have no
  `getIdentifier`. Imported `luci.sys` names are not same-file
  declarations.
- Call resolution (`viableSourceCallable` stays `none()`).
- Return-to-out is `jumpStep` to `OutNode` (see
  `docs/m4-return-out.md`). Do not wire ParameterNode into
  production taint or `path_found`.
- MaD `SourceElement` / `SinkElement` are not in dataflow 1.1.6 `Public`.
- Do not wire summary steps into `localFlowStep`.
