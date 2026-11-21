# Bounded markup CFG proposal (#57)

This is a proposed contract, not an implemented CFG or a statement about template runtime semantics. The current `codeql.ucode.Markup` API exposes generated `UcodeMarkup` AST nodes only; the existing CFG takes the separate plain `ucode::AstNode` type. Neither a conversion nor flow from markup exists today. Keep routing `inconclusive` / `markup_not_modeled` until coverage has been established separately. This proposal does not cover data flow, output escaping, dispatcher behavior, or security conclusions.

## Graph boundary and identities

Introduce a separate markup CFG API initially, with a top-level scope identified by its `UcodeMarkup::Markup` root and AST-backed nodes identified by the exact generated AST node, not by source text or location alone. Locations below are inclusive and are assertions about AST identity; CFG nodes can eventually split, so tests should also identify their scope and role. Use synthetic entry and normal-exit nodes keyed by the scope and role; they have no AST identity. An expression tag has a distinct tag-completion node keyed by its `ExpressionTag`, after its child expression. A `RawText` node represents traversal of that literal fragment; it does not claim an output side effect. A `TextStatement` is a sequence container, not an extra executable node. Delimiters and comments are not executable nodes. Do not equate markup nodes with plain CFG or data-flow nodes.

Sequence children by their AST parent indexes, not by sorting spans or text. Descend through sequence containers. For a supported expression, enter its first evaluation node and finish at its expression node; then visit its tag-completion node. For supported statements, use their expression evaluation followed by their statement completion, then resume the enclosing sequence. A callable body must have its own scope and must not be traversed when its function expression is created. Only normal completion crosses to the next sequence item; abrupt completion, conditionals, loops, and calls require explicit rules before they are supported. Unsupported or recovered syntax must not acquire a guessed fall-through edge; expose the limitation to callers and do not claim the whole file is covered.

## First implementable slice

Start with clean markup roots containing raw text, identifier expression tags, and a lexical declaration with a simple literal initializer, including a transition through `TextStatement`. Define AST-backed nodes for the raw text, identifier, tag, initializer, and declaration and synthetic entry/exit. Connect only this closed subset; no generic fallback that walks arbitrary AST children. This is an ordering contract to validate, not proof of actual rendering or identifier resolution. Require successful extraction with no diagnostics for the fixture. Missing children, parse recovery, and all unsupported expression or statement kinds must fail the coverage predicate and must not silently produce a complete entry-to-exit graph.

The existing `tests/data/markup/usr/share/ucode/controls/mixed.ut` supplies this exact expected ordered path (all edges normal):

| Order | Proposed identity | AST evidence |
| --- | --- | --- |
| 0 | synthetic entry | `Markup` root, 1:1–2:30 |
| 1 | `RawText` | 1:1–1:6, parent `Markup`, index 0 |
| 2 | `Identifier` `name` | 1:10–1:13, parent `ExpressionTag`, index 1 |
| 3 | `ExpressionTag` completion | 1:7–1:16, parent `Markup`, index 1 |
| 4 | `RawText` | 1:17–1:18, parent `Markup`, index 2 |
| 5 | literal initializer `1` | child of declaration at 2:4–2:13; verify its generated kind, parent index and exact span in a new AST assertion before fixing the CFG expectation |
| 6 | `LexicalDeclaration` completion | 2:4–2:13, parent `Markup`, index 4 |
| 7 | `RawText` `Value ` | 2:17–2:22, parent `TextStatement`, index 1 |
| 8 | `Identifier` `x` | 2:26–2:26, parent `ExpressionTag`, index 1 |
| 9 | `ExpressionTag` completion | 2:23–2:29, parent `TextStatement`, index 2 |
| 10 | `RawText` newline | 2:30–2:30, parent `TextStatement`, index 3 |
| 11 | synthetic normal exit | same scope as entry |

The declaration's binding identifier `x` at 2:8 is not an identifier-read node in this slice. The above path is a proposed expectation; only the listed AST rows except the initializer are already asserted by `scripts/markup-ast-smoke.py`. Assert the initializer independently before implementing the path. Assert the complete node and immediate-edge sets, roles, scope membership and exact AST identities, including absence of extra edges, rather than just reachability. Check that the nested text sequence rejoins the root sequence, and add a second small fixture with repeated identical text/identifiers to ensure identities do not collapse by value. Add empty text, adjacent tags, unsupported syntax and malformed `{{ }}` controls: malformed extraction currently yields two diagnostics and must not pass coverage or yield a claimed complete graph. Run these against fresh databases and check exact selected files and extraction diagnostics, as the existing smoke does.

## Real control and subsequent expansion

The pinned `tests/data/markup/usr/share/ucode/luci/uhttpd.uc` is a separate real AST control, not an acceptance test for the first slice. Existing assertions identify imports at 3:1–3:39 and 4:1–4:32 as `Markup` children 1 and 2, and an assignment at 6:1–12:1 inside an `ExpressionStatement`, with its function expression at 6:25–12:1 as assignment child 2. Once imports and assignment/function creation receive explicit rules, a test should assert the first import precedes the second and both precede the top-level assignment; the function body at lines 7–11 belongs to a separate callable scope and is not on that top-level creation path. Do not assert a full node sequence or clean CFG coverage for this real file until the remaining kinds and their exact identities are independently checked. The source pin and hash are recorded in [markup-ast.md](markup-ast.md).

Before adding calls, branching, alternate statement syntax, loops, exceptions, or cross-tag control structures, specify their evaluation, completions, nested scopes and unsupported cases with positive and negative exact-edge fixtures. Verify behavior against an authoritative ucode runtime or grammar evidence before describing it as runtime semantics. Existing plain CFG conventions can inform the design but cannot establish markup behavior by themselves.
