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
whose uniquely declared owner is returned by the first direct top-level
return after a direct top-level assignment. The query excludes selected
same-file declarations, imports, formals, and writes for the presumed
builtins `trim`, `push`, `join`, and `replace`. These are conservative syntax
checks across the whole file: an unrelated later or sibling binding can
suppress a candidate. They are not name resolution or runtime reachability.
Matching syntax does
not prove registration, helper behavior, authorization, or shell execution.
A conditional early return, table declaration after assignment, other
shadowing forms, and other command or quoting shapes remain unknown.

[`expected.json`](expected.json) pins the historical LuCI Tailscale parent and
fix bytes and eighteen derived controls. `renamed_pos.uc` changes the command,
option, field, and handler-formal spellings. `renamed_fixed.uc` quotes the
whole shell argument; `renamed_constant.uc` passes a constant at the same
sink; `renamed_reassigned.uc` overwrites the formal; `unreturned_method.uc`
returns another object; and `different_object_same_method.uc` returns a
different object with the same method name. `push_after_join.uc` moves the
push after command initialization; `nested_helper_decoy.uc` puts the quoting
return in an unused nested helper; `helper_other_replacement.uc` changes the
reviewed quote-helper return shape. `outer_escape.uc` adds an escape to the
outer prefix. `helper_escape.uc` changes the helper replacement escape.
`assignment_after_return.uc` places the assignment after the top-level
return; `conditional_assignment.uc` encloses it in a top-level `if`.
`shadow_trim.uc`, `shadow_push.uc`, `shadow_join.uc`, `shadow_replace.uc`,
and `shadow_import_trim.uc` introduce visible local or imported bindings.
All seven matched the prior query at the same sink shape. Their zero results
under this query mark exclusions,
not safety judgments. The expected candidate locations use inclusive source
columns. SARIF end columns are exclusive.

The historical parent has two distinct field-name witnesses at one sink
entity: `loginserver` and `loginserver_authkey`. SARIF groups their messages
into one result. The opt-in gate and standalone verifier check BQRS
field/location/AST-ID tuples and grouped SARIF messages separately. These
witnesses do not establish
unique field-read entities or resolved data flow.

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
