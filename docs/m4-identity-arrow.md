# M4: Identity `x => x` body identifier is an SSA read

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
`viableSourceCallable` stays `none()`. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- Binding scope of a named formal is the function/arrow body. For an
  identity expression body (`x => x`) that body *is* the identifier,
  so `visibleAt` must use `getParent*()` (not `getParent+()`) or the
  body is not a `VariableReadAccess`.
- That access makes the formal a `SourceVariable`, so it gets the
  existing SSA write at its CFG node. `parameterToSsaDef` then
  continues into `ssaDefToRead` at the body identifier.
- Smoke reports `identity-access identx` and `identity-local 0:identx`
  on `ssa_pos`. `#28` `arrowx => arrowx || 0` stays a child read, not
  an identity row. luci has no identity arrows.
- `jumpStep` stays out of `localFlowStep`. `Call.getArguments()` stays
  `none()`. Summary steps stay out of `localFlowStep`.

## Gaps (later PR)

- Unused formals (`formal_order`'s `a`, luci `_` / `m`) still have no
  `getAnAccess()`, so they still have no `SourceVariable` write.
- Function expressions and arrows are still not `simpleIdentifierCall`
  targets. This step is intra-procedural, not call resolution.
- Return-to-out / `OutNode`. Do not inhabit `viableSourceCallable`.
- MaD `SourceElement` / `SinkElement` are not in dataflow 1.1.6 `Public`.
- Do not wire summary steps into `localFlowStep`. Do not wire
  ParameterNode into production taint or `path_found`.
