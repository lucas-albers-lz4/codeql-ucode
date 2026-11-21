# Investigation: one identifier-copy receiver alias

This is a design investigation for #48 beyond the direct-declarator source observer from #132. It considers exactly one source-level transfer, `let alias = fd`, where `fd` is initialized by the source-declared `fs.popen` and a member call uses `alias`. It does not define a runtime resource identity or imply that `popen` succeeded.

`ql/test/receiver-provenance/alias-transfer-controls.uc` separates three cases:

- `direct_copy`: one identifier copy, then `alias.read` and `alias.close`. A bounded analysis would need to connect the alias initializer's identifier read to each member-call receiver.
- `reassigned_before_use`: the alias is overwritten before either call. A flow-sensitive relation must not attribute either call to the original `popen` value.
- `reassigned_after_use`: `alias.read` precedes the overwrite while `alias.close` follows it. This distinguishes per-use reaching identity from a same-function lexical association.

These cases are not included in the #132 expected rows: its allowlist rejects assignment writes, and its observer follows the lexical binding to the `popen` declarator. Adding the alias case therefore requires extracted evidence of the relevant write/read relationship and separate outcomes at the two uses; source spelling alone is insufficient. The controls include an unrelated same-name receiver and a direct non-alias baseline.

## Extracted result

The controls were extracted in a fresh database with the pinned CodeQL CLI 2.27.4 and the repository-built extractor pack. The pre-finalization routing receipt selected exactly `alias-transfer-controls.uc` (`plain_route_selected`); `SuccessfullyExtractedFiles` contained exactly that file; `ExtractionErrors` returned zero rows.

`ql/src/m4/ReceiverAliasFlow.ql` requires the member expression to equal `call.getFunction()` and matches the receiver access to the exact AST object via `toTreeSitter(receiverAccess.getAstNode()) = member.getObject()`. It returned 18 complete call witnesses. A bare `alias.read` property value in `direct_copy` is excluded. The direct-receiver baseline and a separate `unrelated_same_name` function (where `alias` is initialized from the `other` formal) pin both the ordinary receiver read and a same-spelled but unrelated binding. The rows discriminate the intended cases:

| Control | Reaching writes reported at member receivers |
| --- | --- |
| `direct_copy`, `read` line 7 / `close` line 8 | Both calls are reached from the `fd` declaration initialized by `popen` (line 4) and the alias declaration (line 5); the bare property access on line 6 produces no call row. |
| `direct_receiver`, `read` line 13 / `close` line 14 | Calls on the original `fd` receiver are reached from its `popen` declaration (line 12). |
| `unrelated_same_name`, `read` line 19 / `close` line 20 | Calls on the same-spelled `alias` are reached from the `other` formal (line 17) and alias declaration (line 18); no definition from `direct_copy` reaches them. |
| `reassigned_before_use`, `read` line 27 / `close` line 28 | Both calls are reached from the `other` formal and the reassignment write (line 26); the original `fd` definition does not reach either use. |
| `reassigned_after_use`, `read` line 34 | Reached from the original `fd` declaration (line 32) and alias declaration (line 33). |
| `reassigned_after_use`, `close` line 36 | Reached from the `other` formal and reassignment write (line 35); the original `fd` definition does not reach this use. |

This supports observed intra-procedural flows for these extracted source shapes. It is a materially discriminating candidate for #48 beyond #132's direct initializer observer, which rejects recognized writes and cannot follow the alias declaration. The query is still a prototype: `localFlowStep+` permits multiple transfers and the query does not enforce the proposed one-copy contract; it does not constrain its source definition to a `popen` initializer, address failure/runtime behavior, escapes, reflection, or general aliasing, or claim a resource identity. It does not justify production models, runtime targets, taint, security findings, or `path_found`.

Build and extraction checks: `cargo test --workspace` passed (12 extractor tests, 3 grammar tests, 1 doctest). `bash scripts/m4-receiver-alias-smoke.sh` builds the fresh database, pins the pre-finalization routing receipt, exact successful-file identity, zero extraction errors, and all full spans and labels with multiplicity. Database artifacts from the latest run are in `/tmp/ucode-alias-flow-run2`. Continue to keep #48 production work blocked pending a reviewed design and broader source-derived controls.
