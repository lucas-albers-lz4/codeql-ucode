# M4: ParameterNode from named formals with CFG nodes

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
`viableSourceCallable` stays `none()`. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- `TSourceParameterNode` is inhabited from named formals that already
  have an expression CFG node: block-bodied functions after #24, and
  expression-bodied arrows after #28 (`arrowx` / `arrowa` / `arrowb` /
  `arrowxs` on `ssa_pos`, plus luci `i` / `n` / `port` / block-bodied
  `s`).
- DataFlowDispatch `sourceParameterCfg` overlays those CFG nodes onto
  `ParameterPosition` of the body's `CfgScope`. Public `ParameterNode`
  follows.
- Call arguments that `Call.getArgument` already returns become
  `ArgumentNode`s. `parameterMatch` joins those argument positions to
  parameter positions. That is not call resolution.
- Smoke reports `0:param` / `0:request` / `1:b` / the #28 arrow formals
  on `ssa_pos`, `0:s` / `0:i` / `1:n` / `0:port` on `luci`, plus
  `arg-param 0` on both files.
- `Call.getArguments()` stays `none()`. Summary steps stay out of
  `localFlowStep`. A formal that also has an SSA write continues from
  that `ParameterNode` through `parameterToSsaDef` (see
  `docs/m4-jump-local.md`). Unused formals still have no write.

## Gaps (later PR)

- Unused expression-arrow formals (`_` / `m` in luci `(_, n) =>` /
  `(m, n) =>`) still have CFG nodes, so they can be ParameterNodes, but
  they have no SSA write (`SourceVariable` still requires
  `getAnAccess()`). Smoke does not require those names.
- Identity bodies (`x => x`) count the body identifier as an access
  (see `docs/m4-identity-arrow.md`). The #28 fixture still uses
  `x => x || 0` so that read remains a child.
- Call resolution (`viableSourceCallable` stays `none()`).
- Do not wire ParameterNode into production taint or `path_found`.
- MaD `SourceElement` / `SinkElement` are not in dataflow 1.1.6 `Public`.
- Do not wire summary steps into `localFlowStep`.
