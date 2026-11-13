# M4: Expression-bodied arrows get an inner CfgScope

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
`viableSourceCallable` stays `none()`. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- Expression-bodied arrows (`x => expr`, `(a, b) => expr`) use the
  canonical body expression as a `CfgScope`, analogous to the
  `StatementBlock` scope of block-bodied functions.
- Named formals (`identifier`, rest-element identifier, or a bare
  arrow `parameter`) are the first CFG nodes of that body scope and
  are SSA writes, not `VariableWriteAccess`. `getCfgScope` maps those
  formals to the body, not the enclosing function.
- The body expression keeps its existing CFG tree (evaluation,
  short-circuit, optional). Smoke reports `arrowx` / `arrowa` /
  `arrowb` / `arrowxs` on `ssa_pos` (extractor glob already includes
  that basename) and `i` / `n` / `port` on `luci`. `ParameterNode`
  stays uninhabited.
- Only direct identifier formals and rest-identifier formals are
  modeled. The locked grammar does not parse defaulted or destructured
  bindings (`a = 1` is `ERROR(number)`), so those forms are not in
  fixtures.

## Gaps (later PR)

- Unused expression-arrow formals (`_` / `m` in luci `(_, n) =>` /
  `(m, n) =>`) have no `getAnAccess()`, same as unused block-bodied
  `a` on `ssa_pos`. `codeql/ssa` only constructs WriteDefinitions that
  reach a `variableRead`. Do not invent a pseudo-read.
- Identity bodies (`x => x`) count the body identifier as an access
  (`visibleAt` walks `getParent*()`; see `docs/m4-identity-arrow.md`).
  The #28 fixture still uses `x => x || 0` so that read remains a child.
- Defaulted or destructured formals are not in the locked grammar
  (`a = 1` is `ERROR(number)`). Do not add those fixtures.
- `ParameterNode` / argument-to-parameter flow. Do not add
  `TSourceParameterNode` here.
- `DataFlowDispatch` parameter overlay stays later.
- Do not wire formals into production taint or `path_found`.
