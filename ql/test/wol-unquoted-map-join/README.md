# Testing-only WOL map/join candidate fixtures

`expected.json` pins all 28 source-staged file hashes, expected extraction
identities, zero extraction errors, two candidate locations and 26 zero-row
paths. The real `luci.wol` bytes came from LuCI commit
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
