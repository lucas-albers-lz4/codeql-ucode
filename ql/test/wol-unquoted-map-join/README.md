# Testing-only WOL map/join candidate fixtures

`expected.json` now pins 32 source-staged file hashes, expected extraction
identities, zero extraction errors, four candidate locations and 28 zero-row
paths. The original query was evaluated on all 32 controls with zero extraction errors;
the scoped product layout has separate validation. The real `luci.wol` bytes came from LuCI commit
`b2e0be4b46ec0fd43394c081fa7c50657af14011`; the `installed/` prefix
models the source-to-installed path and does not prove package-member bytes.
The remaining files are synthetic controls for callback binding, quote-body,
import, handler, local-write and command-assembly shapes.

The query uses a file-wide, single-use top-level callback-name condition.
It leaves a file with a direct `eval` call unclassified because the dynamic
call could change that binding. `callback_dynamic_eval.uc` contains a
constant-returning replacement string; the separate no-eval probe reported
a candidate at its line 8 while the testing query did not. This establishes
only a source-level discriminator. Runtime `eval` behavior, indirect dynamic
evaluation, registered RPC ownership, actual `fs.popen` callee resolution,
shell quote context and vulnerability are not determined here.

The exact query and fresh local 28-file receipt are recorded in the coverage
ledger. This rule is outside `code-scanning.qls` and the versioned release.

The `nested_formal_shadow.uc` control selects a different local `request` in a
nested block and includes a nested function with its own formal; it must not be
attributed to the handler formal. `path_binding_shadow.uc` shadows the top-level
`etherwake` value: it remains a candidate, but must report `no-matching-comparison`
instead of claiming the top-level fixed-path guard. These are source-shape
controls, not runtime or security assertions.
The `nested_capture_write.uc` and `nested_formal_disjoint.uc` pair differs only
in the helper's same-spelled formal. The former writes a member through the captured handler formal and is excluded;
the latter writes through its own formal and remains a candidate.

The testing query restricts its binding model to files with a necessary source-shape
seed. The smoke checks that the scoped model is reconstructed exactly from the
shared Variables model and verifies the independently pinned seed before running.
