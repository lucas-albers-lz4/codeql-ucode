# M4: Named formals are Variables with CFG nodes

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
`viableSourceCallable` stays `none()`. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- Named `FormalParameters` children (`identifier` or `rest_element`
  identifier) and a bare arrow `parameter` field are `Variable`s.
  Binding scope is the function body. They are SSA writes, not
  `VariableWriteAccess`.
- Block-bodied functions inject those formals as the first CFG nodes
  of the existing body `StatementBlock` scope. `getCfgScope` maps the
  formal identifier to that body, not the enclosing program.
- Smoke reports `param` / `request` on `ssa_pos` and `s` on `luci`,
  each with a CFG node and an SSA write. `ParameterNode` stays
  uninhabited.

## Gaps (later PR)

- Expression-bodied arrows (`x => expr`) have no inner `CfgScope`, so
  those formals are Variables without a CFG node. Do not put them in
  the enclosing function's CFG.
- `ParameterNode` / argument-to-parameter flow. Do not add
  `TSourceParameterNode` here.
- `DataFlowDispatch` parameter overlay stays later.
- Do not wire formals into production taint or `path_found`.
