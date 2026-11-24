# Bounded markup CFG

`codeql.ucode.MarkupCFG` exposes a separate graph for the closed subset in
[the proposal](markup-cfg-proposal.md). `MarkupCFG::isCovered` is true only for
roots in a selected file without extraction diagnostics whose syntax is limited
to raw text, simple identifier expression tags, and single-variable lexical
declarations with number initializers, including transitions through text
statements. An identifier expression tag can independently use an ordinary or
trim token at each delimiter. Comments, shebangs, recovered syntax, and other constructs are not
covered. A shebang represented as the first raw text fragment is rejected as
well. Unsupported roots have no nodes or edges in this API.

Each node has a root scope and a role. Entry and exit are synthetic; other
nodes retain their exact generated markup AST identity. `edge` describes only
immediate normal ordering within covered roots. Sequence order uses AST parent
indexes. The graph is distinct from the plain ucode CFG and data flow, and it
does not establish rendering, resolution, output escaping, security coverage,
or dispatcher behavior. Routing remains `inconclusive` / `markup_not_modeled`.

`scripts/markup-cfg-smoke.py` creates fresh databases and checks the selected
file identities, diagnostics, independent AST identities, and complete node and
edge sets for positive and negative controls. `scripts/markup-ast-smoke.py`
also independently checks the mixed declaration and initializer identities.
