# Investigation: one identifier-copy receiver alias

This is a design investigation for #48 beyond the direct-declarator source observer from #132. It considers exactly one source-level transfer, `let alias = fd`, where `fd` is initialized by the source-declared `fs.popen` and a member call uses `alias`. It does not define a runtime resource identity or imply that `popen` succeeded.

`ql/test/receiver-provenance/alias-transfer-controls.uc` separates three cases:

- `direct_copy`: one identifier copy, then `alias.read` and `alias.close`. A bounded analysis would need to connect the alias initializer's identifier read to each member-call receiver.
- `reassigned_before_use`: the alias is overwritten before either call. A flow-sensitive relation must not attribute either call to the original `popen` value.
- `reassigned_after_use`: `alias.read` precedes the overwrite while `alias.close` follows it. This distinguishes per-use reaching identity from a same-function lexical association.

These cases are not included in the #132 expected rows: its allowlist rejects assignment writes, and its observer follows the lexical binding to the `popen` declarator. Adding the alias case therefore requires extracted evidence of the relevant write/read relationship and separate outcomes at the two uses; source spelling alone is insufficient. Controls should also include unrelated same-name locals and a direct non-alias baseline before any relation is proposed.

## Extracted result

The controls were extracted in a fresh database with the pinned CodeQL CLI 2.27.4 and the repository-built extractor pack. The pre-finalization routing receipt selected exactly `alias-transfer-controls.uc` (`plain_route_selected`); `SuccessfullyExtractedFiles` contained exactly that file; `ExtractionErrors` returned zero rows.

`ql/src/m4/ReceiverAliasFlow.ql` reports source SSA definitions that reach a variable read used as a direct member-call receiver through `DataFlow::localFlowStep+`. It returned 12 rows: four per function. The rows discriminate the intended cases:

| Control | Reaching writes reported at member receivers |
| --- | --- |
| `direct_copy`, `read` line 6 / `close` line 7 | Both calls are reached from the `fd` declaration initialized by `popen` (line 4) and the alias declaration (line 5). |
| `reassigned_before_use`, `read` line 14 / `close` line 15 | Both calls are reached from the `other` formal and the reassignment write (line 13); the original `fd` definition does not reach either use. |
| `reassigned_after_use`, `read` line 21 | Reached from the original `fd` declaration (line 19) and alias declaration (line 20). |
| `reassigned_after_use`, `close` line 23 | Reached from the `other` formal and reassignment write (line 22); the original `fd` definition does not reach this use. |

This supports a narrow **intra-procedural, per-use identifier-copy relation** for these extracted source shapes. It is a materially discriminating candidate for #48 beyond #132's direct initializer observer, which rejects recognized writes and cannot follow the alias declaration. The query is still a prototype: it does not constrain its source definition to a `popen` initializer, does not address failure/runtime behavior, escapes, reflection, or general aliasing, and does not claim a resource identity. It does not justify production models, runtime targets, taint, security findings, or `path_found`.

Build and extraction checks: `cargo test --workspace` passed (12 extractor tests, 3 grammar tests, 1 doctest); the fresh extracted database had one selected file, zero extraction errors, and the alias-flow query compiled and returned the 12 rows above. Database artifacts are in `/tmp/ucode-alias-flow-run` for this run. Continue to keep #48 production work blocked pending a reviewed design and broader source-derived controls.
