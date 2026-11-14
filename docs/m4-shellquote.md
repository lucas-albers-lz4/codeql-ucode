# M4: `shellquote` candidate retention

`shellquote` is **not** a global sanitizer. No implementation currently has a trusted semantic model, so v2 does not suppress any candidate based on that name. Absence of a same-file declaration does not establish that an unresolved identifier is a trusted builtin. The real luci fixture defines a local helper whose semantics are not yet modeled.

| Fixture / method | Taint reaches sink | Complete-argument barrier | Shell-injection candidate |
| --- | --- | --- | --- |
| `taint_pos` | yes | no | **yes** |
| `quote_ok*` fixtures (every matching fixture is asserted) | yes | no (unknown helper) | **yes** |
| `quote_exe` | yes | no (whole command) | **yes** (executable selection) |
| `taint_neg` | no | — | no |
| luci `getSwconfigFeatures` / `getSwconfigPortState` | yes | no (local helper) | **yes** |
| `quote_bad_*` | yes | no | **yes** |

An independent `ShellquoteTemplateShape` regression query checks necessary syntactic conditions for a future barrier: a direct, unchanged call in the first substitution after a literal `swconfig`, `echo`, or `printf` command, with whitespace word boundaries, and nothing after that substitution's trailing fragment — a later substitution is unquoted program text and is rejected. Any same-file identifier occurrence outside a direct callee rejects the shape. This conservative file-wide check is not scope-aware binding resolution and does not prove quoting semantics.

The smoke gate tests `sh`, `ash`, `bash`, interpreter paths, combined flags and wrappers; transformations and conditionals; separator/pipe command positions; joined words; local function, variable, parameter, import and assignment bindings; and direct non-interpreter shape controls. It also requires zero actual barriers and retains the untainted negative control. Every `quote_ok*` fixture discovered in the fixture directory must appear in both the supported-shape and retained-candidate query results. The luci query explicitly selects the enclosing method plus source and sink start lines (not the AST-valued column 0, which CodeQL CSV renders as `MemberExpression`) and pins exact method/sink/source-line/sink-line tuples, distinguishing separate taint sources at a single call site. `scripts/m4-smoke.sh` independently pins the RequestArgsExec method/sink distribution. Parenthesized calls, later substitutions and general shell grammar remain unsupported.

Run `scripts/m4-quote-smoke.sh` for extraction and all three actual CodeQL queries. This conservative repair increases candidates and makes no vulnerability claim. The JSON snapshots mark former `no_path` conclusions inconclusive; historical record IDs remain stable for interchange compatibility. The corpus lock is provenance metadata, not evidence of a full pinned-corpus rerun. No ucode runtime execution is claimed.
