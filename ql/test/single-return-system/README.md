# Single-return fixed-system source-shape smoke

Run `bash scripts/m4-single-return-system-shape-smoke.sh` after preparing the
normal extractor pack and CodeQL dependencies. The aggregate M4 glob selects it
once. Set `SINGLE_RETURN_KEEP_EVIDENCE=1` to retain the isolated temporary
source tree, routing receipt, database and BQRS outputs; otherwise they are
removed on exit.

The query is a testing table for a narrow source shape: a source-declared
`luci.setBlockDetect` callback consists of one return containing only a
`result` property whose expression is a syntactically supported builtin
`system` call with one plain string argument compared to zero. The models'
builtin relation is a syntactic approximation, not runtime target identity.
The exact call-site full spans and command strings are checked as a multiset.
The real source is the existing vendored LuCI fixture pinned to
`b2e0be4b46ec0fd43394c081fa7c50657af14011`; the other inputs are synthetic.
Commands in fixtures are never executed.

The smoke checks fifteen exact successful-file identities and no extraction
errors before querying. It accepts the three positive call sites and excludes
all twelve negative inputs. It also compiles and evaluates three real QL mutants:
removing the one-statement veto or the string-child veto, or shifting the
reported start column without changing the row count. Each must yield exactly
its independently specified row multiset and fail the unchanged oracle.
The separate Python tests exercise diagnostic identity and error rejection,
including missing, duplicated and substituted identities. A composed-smoke
replay also runs the actual shell script with a strict synthetic CodeQL shim:
it checks command operands and flags, a pristine path, and that each rejected
receipt stops before any semantic query. Its synthetic rows verify wiring, not
CodeQL semantics or fresh extraction.

A nonmatch is **unassessed**, not safe. This table is not a missing-guard or
authorization finding and says nothing about runtime registration, execution,
ingress ACLs, called-command checks, taint, exploitability or access control.
It does not implement or validate a downstream consumer, policy grant or
report promotion. The staged `modules/<case>/...` layout is for this test;
no consumer compatibility is asserted.
