# Nested RPC shell command candidate

`NestedRpcShellCommand.ql` is a testing-tagged, syntactic candidate. It is not
in the default code-scanning suite. The draft Linux regression workflow opts in
explicitly to its matrix; the tag-publishing release gate does not run that
matrix. The release bundle includes the `ql/src` pack, including this query,
for explicit testing use. The query recognizes one bounded source
shape: a field of an RPC call formal is trimmed, quoted by a same-file helper,
pushed into an array, joined into a literal-prefixed command, and passed to an
imported `fs.popen` in the old outer `'/bin/sh -c "' + command + ' &"'` form.
The handler must be the exact `call` function in an assigned method object
whose uniquely declared owner is returned at top level. Matching source
syntax does not prove runtime registration, helper behavior, reachability,
authorization, or shell execution. The query does not prove that the owner
was returned after its method assignment, or resolve the global `replace`
binding. Other command and quoting shapes remain unknown.

[`expected.json`](expected.json) pins the historical LuCI Tailscale parent and
fix bytes and eleven derived controls. `renamed_pos.uc` changes the command,
option, field, and handler-formal spellings. `renamed_fixed.uc` quotes the
whole shell argument; `renamed_constant.uc` passes a constant at the same
sink; `renamed_reassigned.uc` overwrites the formal; `unreturned_method.uc`
returns another object; and `different_object_same_method.uc` returns a
different object with the same method name. `push_after_join.uc` moves the
push after command initialization; `nested_helper_decoy.uc` puts the quoting
return in an unused nested helper; `helper_other_replacement.uc` changes the
reviewed quote-helper return shape. `outer_escape.uc` adds an escape to the
outer prefix. `helper_escape.uc` changes the helper replacement escape. Their
zero results mark query exclusions,
not safety judgments. The expected candidate locations use inclusive source
columns. SARIF end columns are exclusive.

For each run, verify the source hashes before extraction, use a fresh database
and run-owned caches, and record the selected producer, extractor, grammar,
CodeQL and lock identities. Run `SuccessfullyExtractedFiles.ql`,
`ExtractionErrors.ql`, this query, and explicit SARIF analysis. Decode the
diagnostics as JSON, then validate them and the SARIF with
`scripts/nested-rpc-shell-command-verify.py --run <run-root>`. The verifier
checks supplied artifacts; it does not authenticate when or how they were
produced. A Linux job using an immutable producer artifact remains required
before this candidate can enter any release contract.

Local development retained the initial zero-result query caused by an
incorrect `rpcCallFn` pair-shape guard under ignored `work/`. A later fixture
revision corrected a predeclared column-span mismatch. The earlier
eleven-file run and a separate 17-file current LuCI rpcd source-staged run
are recorded in the ledger's ignored `work/` tree, not distributed with this
test. The current-source zero result is a bounded observation, not a safety
finding.
