# M4: `jumpStep` ParameterNode continues into SSA `localFlowStep`

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Unique same-file identifier FunctionDeclarations may resolve;
imported `luci.sys` stays unresolved. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- `#30` `jumpStep` lands on `TSourceParameterNode`. That node is not
  the SSA write of the formal, so public `localFlowStep` did not
  continue into `ssaDefToRead`.
- `parameterToSsaDef` takes a named formal `ParameterNode` whose CFG
  node is already that formal's SSA write into the corresponding
  `SsaDefinitionNode`. Existing `ssaDefToRead` then reaches uses.
- `jumpStep` itself stays out of `localFlowStep`. `Call.getArguments()`
  stays `none()`. Summary steps stay out of `localFlowStep`.
- Smoke reports `jump-local 0:s` from `shellquote` and `0:pkg` from
  `callPackageVersionCheck` on `luci`, `jump-local 1:b` from
  `formal_order` on `ssa_pos`, plus `param-local` for `ssa_pos`
  formals that have an SSA read (`request`, inner `param`) without a
  jump. Unused `formal_order` `a` has no SSA read, so it has no
  jump-local row. Builtin `system(...)` still does not enter
  `formal_order`.

## Gaps (later PR)

- Unused formals (`formal_order`'s `a`, luci `_` / `m`) have
  ParameterNodes but no `getAnAccess()`, so `codeql/ssa` constructs no
  WriteDefinition. Do not invent a pseudo-read. Identity `x => x` is
  an access of the formal (see `docs/m4-identity-arrow.md`).
- Function expressions and arrows are still not `simpleIdentifierCall`
  targets. This step is intra-procedural; unique same-file identifier
  FunctionDeclarations inhabit `viableSourceCallable` separately.
- Return-to-out is `jumpStep` to `OutNode` (see
  `docs/m4-return-out.md`).
- MaD `SourceElement` / `SinkElement` are not in dataflow 1.1.6 `Public`.
- Do not wire summary steps into `localFlowStep`. Do not wire
  ParameterNode into production taint or `path_found`.
