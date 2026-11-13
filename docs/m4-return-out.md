# M4: `ReturnValueNode` jumps to same-file identifier `OutNode`

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Unique same-file identifier FunctionDeclarations may resolve;
imported `luci.sys` stays unresolved. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- `#30` `jumpStep` takes arguments into a same-file identifier
  declaration's `ParameterNode`. The dual was missing: `ReturnNode` was
  already inhabited (`ReturnValueNode` / `expressionToReturn`), but
  `OutNode` was empty, so the return never left the callee.
- `OutNode` is the call expression (`CallCfgNode` is an `ExprCfgNode`).
  `jumpStep` takes that declaration's `ReturnValueNode` to each
  `simpleIdentifierCall` `OutNode`. Same evidence as `#30`, not a call
  graph. Unique same-file identifier FunctionDeclarations inhabit
  `viableSourceCallable` separately.
- `jumpStep` stays out of `localFlowStep`. `Call.getArguments()` stays
  `none()`. Summary steps stay out of `localFlowStep`.
- Smoke reports `out` / `jump-out` for `shellquote` and
  `callPackageVersionCheck` on `luci`, plus `formal_order` on
  `ssa_pos`. Builtin `system(...)` still does not enter
  `formal_order`.

## Gaps (later PR)

- Unused formals (`formal_order`'s `a`, luci `_` / `m`) have CFG nodes
  but no `getAnAccess()`. `codeql/ssa` only constructs WriteDefinitions
  that reach a `variableRead`. Do not invent a pseudo-read.
- Function expressions and arrows are still not `simpleIdentifierCall`
  targets. This step is intra-procedural, not call resolution.
- Member, subscript, parenthesized, and nested-call callees have no
  `getIdentifier`. Imported `luci.sys` names are not same-file
  declarations.
- Unique same-file identifier FunctionDeclarations inhabit
  `viableSourceCallable` separately. `jumpStep` still uses unfiltered
  `simpleIdentifierCall`.
- MaD `SourceElement` / `SinkElement` are not in dataflow 1.1.6 `Public`.
- Do not wire summary steps into `localFlowStep`. Do not wire
  ParameterNode into production taint or `path_found`.
