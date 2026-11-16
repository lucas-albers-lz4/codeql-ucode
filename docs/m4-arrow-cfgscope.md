# M4: Expression-bodied arrows get an inner CfgScope

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Experimental call models can match unique same-file identifier and
member-property function declarations. The models do not resolve imported
`luci.sys` targets. Production `LocalTaint` and `RequestArgsExec` use Models.

## What compiles

- Expression-bodied arrows (`x => expr`, `(a, b) => expr`) use the
  canonical body expression as a `CfgScope`, analogous to the
  `StatementBlock` scope of block-bodied functions.
- Named formals (`identifier`, rest-element identifier, or a bare
  arrow `parameter`) are the first CFG nodes of that body scope and
  are SSA writes, not `VariableWriteAccess`. `getCfgScope` maps those
  formals to the body, not the enclosing function.
- The body expression keeps its existing CFG tree (evaluation,
  short-circuit, optional). The smoke reports `arrowx` / `arrowa` /
  `arrowb` / `arrowxs` on `ssa_pos`, and `i` / `n` / `port` on `luci`.
- Named formals with CFG nodes also have `ParameterNode`s. The parameter
  overlay includes expression-bodied arrows. See [ParameterNode from named
  formals](m4-parameter-node.md).
- The model supports only direct identifier formals and rest-identifier
  formals. The locked grammar does not parse defaulted or destructured
  bindings (`a = 1` is `ERROR(number)`), so those forms are not in
  fixtures.

## Limits and related models

- Unused expression-arrow formals (`_` / `m` in luci `(_, n) =>` /
  `(m, n) =>`) have no `getAnAccess()`, same as unused block-bodied
  `a` on `ssa_pos`. `codeql/ssa` only constructs WriteDefinitions that
  reach a `variableRead`. Do not invent a pseudo-read.
- Identity bodies (`x => x`) count the body identifier as an access.
  `visibleAt` walks `getParent*()`. See `docs/m4-identity-arrow.md`.
  The #28 fixture still uses `x => x || 0` so that read remains a child.
- Defaulted or destructured formals are not in the locked grammar
  (`a = 1` is `ERROR(number)`). Do not add those fixtures.
- Same-file call `jumpStep` uses function declarations as targets. The
  target model does not include arrow expressions. See
  [identifier call jumps](m4-simple-call-jump.md) and
  [member call jumps](m4-member-call-jump.md).
- Production taint and `path_found` do not use these formal-flow models.
