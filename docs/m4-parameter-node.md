# M4: ParameterNode from named formals with CFG nodes

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Experimental call models can match unique same-file identifier and
member-property function declarations. The models do not resolve imported
`luci.sys` targets. Production `LocalTaint` and `RequestArgsExec` use Models.

## What compiles

- `TSourceParameterNode` wraps the expression CFG nodes of named formals.
  These include formals of block-bodied functions after #24 and
  formals of expression-bodied arrows after #28 (`arrowx` / `arrowa` / `arrowb` /
  `arrowxs` on `ssa_pos`, plus luci `i` / `n` / `port` / block-bodied
  `s`).
- DataFlowDispatch `sourceParameterCfg` overlays those CFG nodes onto
  `ParameterPosition` of the body `CfgScope`. Public `ParameterNode`
  follows.
- Call arguments that `Call.getArgument` returns can become
  `ArgumentNode`s when they have CFG nodes in the call scope.
  `parameterMatch` compares argument and parameter positions. This
  comparison does not resolve calls or prove value identity.
- The smoke reports `0:param` / `0:request` / `1:b` and the #28 arrow
  formals on `ssa_pos`. It reports `0:s` / `0:i` / `1:n` / `0:port` on
  `luci`, plus `arg-param 0` on both files.
- `Call.getArguments()` stays `none()`. Summary steps stay out of
  `localFlowStep`. A formal that also has an SSA write continues from
  that `ParameterNode` through `parameterToSsaDef` (see
  `docs/m4-jump-local.md`). Unused formals still have no write.

## Gaps (later PR)

- Unused expression-arrow formals (`_` / `m` in luci `(_, n) =>` /
  `(m, n) =>`) still have CFG nodes, so they can be ParameterNodes, but
  they have no `getAnAccess()`. `codeql/ssa` only constructs
  WriteDefinitions that reach a `variableRead`. Smoke does not require
  those names.
- Identity bodies (`x => x`) count the body identifier as an access
  (see `docs/m4-identity-arrow.md`). The #28 fixture still uses
  `x => x || 0` so that read remains a child.
- Call resolution is a separate smoke (`viableSourceCallable` unique
  same-file FunctionDeclarations). This smoke does not cover
  argument-to-parameter through-flow.
- Do not wire ParameterNode into production taint or `path_found`.
- MaD `SourceElement` / `SinkElement` are not in dataflow 1.1.6 `Public`.
- Do not wire summary steps into `localFlowStep`.
