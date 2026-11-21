# M4: experimental template-string call arguments

This is a bounded language-pack foundation for a template string passed
directly as a call argument. It does not add production taint models or a
`path_found` claim.

## AST and API contract

- `Call.getTemplateArgument(index)` returns the concrete `TemplateString` at
  that zero-based call argument position. It returns no result for a plain
  string, number, or other non-template argument.
- `Call.getArgument(index)` keeps its existing `TExpr` contract, and
  `Call.getArguments()` stays `none()`. The template API is separate because
  widening `TExpr` adds aliases to the same AST entity and changes CFG
  membership; see [`m4-call-get-argument.md`](m4-call-get-argument.md).
- The template's direct children are literal `StringFragment` nodes, escape
  sequence nodes, and `TemplateSubstitution` nodes in source order. Literal
  fragments represent text portions; substitutions are distinct AST nodes.
  The regression query filters for the concrete `StringFragment` class to
  avoid the overlapping generic AST wrappers.
- `TemplateSubstitution.getExpression()` returns a
  `TemplateSubstitutionExpression`, a wrapper around the exact raw expression
  AST entity. Its `getRawAstNode()` can be compared with
  `toTreeSitter(DataFlow::ExprNode.getExprNode().getAstNode())` to preserve
  expression identity without casting the value to the overlapping `Expr`
  union. The control query asserts one canonical call-expression identity for
  each nested call substitution and exact identifiers for the two
  multi-substitution `system` inputs.
- Substitution position is its zero-based order among direct substitution
  children, derived from source order. Call argument position is independent:
  a template at argument 1 can contain substitution 0.

## Evaluation and flow semantics

The AST records parts in source order. The ucode compiler inspected at commit
[`a2c42eac6369a0bba0315007c7dc7b7130275340`](https://github.com/ucode-lang/ucode/blob/a2c42eac6369a0bba0315007c7dc7b7130275340/compiler.c#L2011-L2040)
emits the leading literal, then compiles each interpolation expression and
emits `I_ADD` before advancing to later parts. This supports left-to-right
interpolation evaluation followed by string construction. The repository pins
the LuCI fixture, not that runtime revision; this is compiler-source evidence,
not a claim that the fixture ran under that revision.

The constructed `TemplateString` appears as an `AstCfgNode` in the ordered
evaluation CFG, with incoming and outgoing CFG edges in the named real fixture
and controls. It is not a `DataFlow::ExprNode`. Interpolation expressions keep
their own AST and ordinary CFG identities. No local value-flow edge connects a
literal fragment or substitution expression to the completed string:
interpolation plus `I_ADD` constructs a different value.

The supported surface is direct call arguments and their direct template
parts. Nested templates, tagged forms, template dataflow summaries, coercion
rules for each interpolation type, and source/runtime-specific encoding
details remain outside this foundation. No sanitizer or runtime target is
introduced.

## Regression evidence

`scripts/m4-template-call-arguments-smoke.sh` extracts the pinned `luci` file
and `template_args.uc`, checks exact extracted-file identities and zero
extraction errors, then asserts exact argument, literal fragment,
substitution, wrapper-scope, and expression CFG rows. The named real controls are
`getSwconfigFeatures`' `popen` template at `luci:343` and the three
substitutions in `setPassword`'s `system` template at `luci:474`. Local
controls cover a plain non-template argument, a literal-only template, a
single nested call, multiple substitutions with nested expressions, a
non-template argument before a template at argument index 1, and a trailing
non-template argument.

The same smoke asserts that each tested whole template has its expected
evaluation `AstCfgNode`, while no whole-template `DataFlow::ExprNode` or
literal-or-substitution-to-template `localFlowStep` is reported. Existing
`Call.getArgument` behavior and production `LocalTaint` /
`RequestArgsExec` remain unchanged; `LocalTaint`, `RequestArgsExec`, and
`ImportedCalleeTaint` stay on Models.

Validation used CodeQL CLI 2.27.4 on macOS with the grammar at the revision
recorded by `scripts/clone-grammar.sh`:

| Command | Result |
| --- | --- |
| `./scripts/m4-template-call-arguments-smoke.sh` | Passed: exact extraction multiset, zero errors, exact argument/fragment/substitution/CFG rows, left-to-right CFG paths, no value node for the constructed string, and no value-flow edge to it. |
| `./scripts/m4-call-get-argument-smoke.sh` | Passed: existing argument controls; production `LocalTaint` and `RequestArgsExec` compiled and remained on Models. |
| `./scripts/m4-cfg-smoke.sh` | Passed: existing CFG statement, scope, and return controls. |
| `./scripts/m4-ssa-smoke.sh` | Passed: existing SSA read/write and local-flow positive/negative controls. |

The source-order runtime claim comes from compiler source at the commit linked
above. No ucode runtime was executed, and that compiler revision is not pinned
by the LuCI fixture.
