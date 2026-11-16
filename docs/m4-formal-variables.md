# M4: Named formals are Variables with CFG nodes

Typecheck and extractor-smoke only. Not production taint and not `path_found`.
Unique same-file identifier and member-property FunctionDeclarations may resolve;
imported `luci.sys` stays unresolved. Production `LocalTaint` /
`RequestArgsExec` stay on Models.

## What compiles

- Named `FormalParameters` children (`identifier` or `rest_element`
  identifier) and a bare arrow `parameter` field are `Variable`s.
  Binding scope is the function body. They are SSA writes, not
  `VariableWriteAccess`.
- Block-bodied functions put those formals first in the CFG of the body
  `StatementBlock`. Expression-bodied arrows use the body expression as the
  inner `CfgScope`. The formals belong to the body scope, not the program.
- The formal smoke reports `param` / `request` on `ssa_pos` and `s` on
  `luci`. Each has a CFG node and an SSA write. Named formals with CFG
  nodes also have `ParameterNode`s. See `docs/m4-parameter-node.md`.
- Only direct identifier formals and rest-identifier formals are modeled.
  The locked grammar does not parse defaulted or destructured bindings, so
  those forms are not Variables and cannot live in extractor fixtures.
  Smoke uses two identifier formals on `ssa_pos`: later `b` keeps compact
  parameter order and sits on the CFG before the body return.

## Limits

- The separate expression-arrow smoke checks the body scope. See
  `docs/m4-arrow-cfgscope.md`.
- Same-file call `jumpStep` has a separate scope and regression. See
  `docs/m4-simple-call-jump.md` and `docs/m4-member-call-jump.md`.
- Production taint and `path_found` do not use these formal-flow models.
