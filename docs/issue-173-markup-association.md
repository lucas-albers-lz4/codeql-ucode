# Test-only markup association experiment

This test-only relation associates a direct root `const` declaration with an
identifier interpolation in the immediately adjacent root text statement. It
requires a single initialized identifier declarator, a unique supported root
binding, a clean diagnostic inventory, and a direct identifier tag. Each tag is
an independent entity. Earlier expression tags are inspected for assignment,
augmented assignment and update targets; a same-name identifier write or an
unsupported non-identifier target suppresses the association. Later tags do
not suppress an earlier candidate. Binding-producing function and arrow
expressions and delete expressions in the relevant prefix are unresolved.
Opaque calls are not modeled; their effects are unknown. Export-wrapped declarations
and import local names participate in the competing-binding check. Unbraced
`if`, `else`, and `while` bodies are inspected for declarations that share
the root scope; nested block and alternate-syntax scopes are not traversed.

This is a syntax feasibility test, not a general binding, control-flow, data-flow
or taint model. The initializer and preceding member expression in the pinned
Footstrap source are opaque. It does not establish evaluation, rendering,
escaping, output bytes, runtime value propagation, reachability or security.
No production query imports the relation and markup routing remains
`inconclusive` / `markup_not_modeled`.

Run `python3 scripts/markup-association-smoke.py` with the repository extractor
pack built and the pinned CodeQL CLI available. The staged Footstrap fixture is
from LuCI `b2e0be4b46ec0fd43394c081fa7c50657af14011`, blob
`ed60435eeb98c71c192ffe98b638765a87934445`, SHA-256
`7653f8353e5bb1062b3f5a901e6b2488af5ed59b530f3c5721169f0e8fa32977`.
The parser-level same-name assignment control is not evidence that the native
compiler accepts a write to a constant. The smoke checks exact routes, extracted
file identities, all diagnostic rows, the pinned source anchors, witness parent
entity IDs and child indices, repeated tag identities and a failing mutation.
The aggregate CI runner invokes this check and verifies its failure propagation.
