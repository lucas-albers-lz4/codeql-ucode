# Source-declared namespace fs.stat observation

This model recognizes one-argument static `fs.stat` calls under a unique,
earlier top-level `import * as fs from 'fs'`. It conservatively rejects
competing declarations, direct writes, simple aliases and direct member or
bracket mutations, optional or computed calls, spreads and extra arguments.
It is a bounded source-syntax observation. It does not resolve runtime binding,
object escape, path flow, reachability, sanitization, or security impact;
unsupported calls remain inconclusive. The existing named-import model and
production query behavior are unchanged.

The vendored real fixture and its attribution/license are documented beside
this file. The source-first expectation is one `fs.stat(p)` in
`luci.advanced-reboot` at line 60, plus the synthetic `real-shape.uc` and
`fixed-literal.uc` namespace calls. `named.uc` is the existing named model
control. Other synthetic files each target a rejection condition; source
routing, source archive bytes, exact successful-file identities, extraction
errors and database-local call/callee/argument AST IDs are checked before
accepting model rows. The literal path remains a model member; it is not a
claim of request-derived flow.

`bash scripts/m4-namespace-stat-smoke.sh` requires the existing extractor pack
and CodeQL packs. It runs the explicit testing queries in private paths. The
runner freezes fixture bytes and expected rows before evaluating, checks the
real source's pinned SHA-256 and Git blob, checks plain routing including the
installed-shaped application path, and preserves raw outputs. The query is not
part of a security suite. See the tests for aggregate order and failure
propagation; no CodeQL evidence implies runtime safety.
