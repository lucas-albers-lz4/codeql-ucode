# M4: `jumpStep` from same-file identifier `Call.getArgument` into `ParameterNode`

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Unique same-file identifier and member-property FunctionDeclarations may resolve;
imported `luci.sys` stays unresolved. Production `LocalTaint` /
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
  `callPackageVersionCheck` on `luci`, plus `0:a` / `1:b` from
  `formal_order` on `ssa_pos`. Unique same-file member
  FunctionDeclarations also `jumpStep` (see
  `docs/m4-member-call-jump.md`). Builtin `system(...)` still does not
  enter `formal_order`.
- `Call.getArguments()` stays `none()`. Summary steps stay out of
  `localFlowStep`. Public `localFlowStep` does not include `jumpStep`.
  Body continuation from that `ParameterNode` is `parameterToSsaDef`
  (see `docs/m4-jump-local.md`).

## Gaps (later PR)

- Function expressions (`function(request) { ... }`) and arrows are
  not declarations, so they are not simple-call targets.
- Subscript, parenthesized, and nested-call callees have no
  `getIdentifier` and are not unique member-property declarations, so
  they do not `jumpStep`. Unique same-file member FunctionDeclarations
  jump via `sameFileJumpCall` (see `docs/m4-member-call-jump.md`).
  Imported `luci.sys` names are not same-file declarations.
- Identifier `jumpStep` still uses unfiltered `simpleIdentifierCall`.
  Unique same-file identifier FunctionDeclarations inhabit
  `viableSourceCallable` separately.
- Return-to-out is `jumpStep` to `OutNode` (see
  `docs/m4-return-out.md`). Do not wire ParameterNode into
  production taint or `path_found`.
- MaD `SourceElement` / `SinkElement` are not in dataflow 1.1.6 `Public`.
- Do not wire summary steps into `localFlowStep`.
