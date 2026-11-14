# M4: `shellquote` candidate retention

`shellquote` is **not** a global sanitizer. No implementation currently has a trusted semantic model, so v2 does not suppress any candidate based on that name. Absence of a same-file declaration does not establish that an unresolved identifier is a trusted builtin. The real luci fixture defines a local helper whose semantics are not yet modeled.

| Fixture / method | Taint reaches sink | Complete-argument barrier | Shell-injection candidate |
| --- | --- | --- | --- |
| `taint_pos` | yes | no | **yes** |
| `quote_ok`, `quote_ok_echo`, `quote_ok_printf` | yes | no (unknown helper) | **yes** |
| `quote_exe` | yes | no (whole command) | **yes** (executable selection) |
| `taint_neg` | no | — | no |
| luci `getSwconfigFeatures` / `getSwconfigPortState` | yes | no (local helper) | **yes** |
| `quote_bad_*` | yes | no | **yes** |

An independent `ShellquoteTemplateShape` regression query checks necessary syntactic conditions for a future barrier: a direct, unchanged call in the first substitution after a literal `swconfig`, `echo`, or `printf` command, with whitespace word boundaries. Any same-file identifier occurrence outside a direct callee rejects the shape. This conservative file-wide check is not scope-aware binding resolution and does not prove quoting semantics.

The smoke gate tests `sh`, `ash`, `bash`, interpreter paths, combined flags and wrappers; transformations and conditionals; separator/pipe command positions; joined words; local function, variable, parameter, import and assignment bindings; and direct non-interpreter shape controls. It also requires zero actual barriers and retains the untainted negative control. Parenthesized calls, later substitutions and general shell grammar remain unsupported.

Run `scripts/m4-quote-smoke.sh` for extraction and all three actual CodeQL queries. This conservative repair increases candidates and makes no vulnerability claim. The JSON snapshots mark former `no_path` conclusions inconclusive; historical record IDs remain stable for interchange compatibility. The corpus lock is provenance metadata, not evidence of a full pinned-corpus rerun. No ucode runtime execution is claimed.
