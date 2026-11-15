# Source-declared `fs.readlink` callable

`viableLibraryCallable` identifies a deliberately bounded, **source-declared**
`readlink` import. This is not a runtime module resolver or a flow model.
It requires a CFG-backed call with a plain identifier callee `readlink` and
no optional chain; a preceding top-level, unaliased named `readlink` import;
and an import source consisting of exactly one raw `fs` string fragment, with
no escape or other child. There must be exactly one local `readlink` import
binding in the file, counting named aliases, defaults, namespaces and duplicate
specifiers. Files with an extraction error are excluded.

The entire file must also have no competing `readlink` lexical, function,
function-expression, formal/rest/arrow, catch or loop binding, or assignment,
augmented assignment or update. This is intentionally **not lexical scope
resolution**: an unrelated sibling, later declaration or expired shadow makes
even genuine imported calls unresolved. Aliases, optional calls, members,
subscripts and wrapped callees are unresolved. A source call appearing before
the import is unresolved, even when its enclosing function runs later. A
missing result means unknown, not safe, unreachable, sanitized or not readlink.
Extraction success is not successful ucode compilation or module resolution;
other semantic errors may exist. The source name `fs` does not attest which
module a runtime loader supplies, execution, return values or filesystem state.

## Evidence and scope

An independent single-reviewer `gpt-6.1-sol` honesty audit, using the latest
model allowed by the requester (not Grok), tested runtime binding probes and
actual extracted CodeQL entities. It rejected reusing the existing `readfile`
matcher: local and formal shadows can receive its library target; that separate
defect is tracked in [#85](https://github.com/lucas-albers-lz4/codeql-ucode/issues/85).
It also showed that concatenating only string fragments incorrectly accepts
`'f\x2fs'`, whose runtime module name is `f/s`. The readlink matcher instead
rejects escape children. The audit used producer revision
[`d54c17a8cefc43ef9cde36d65558c986348aa7b2`](https://github.com/lucas-albers-lz4/codeql-ucode/tree/d54c17a8cefc43ef9cde36d65558c986348aa7b2),
[ucode compiler/native fs](https://github.com/jow-/ucode/tree/b885dd0fe1e974551fb1233ca5f3aa74d80b74d9),
and [grammar](https://github.com/m00qek/tree-sitter-ucode/tree/4a243af329fae2f4ff01e0fc80133cbab8314600)
pins. Runtime probes showed direct/nested calls hitting the native fs callable,
local/formal shadows hitting local functions, and calls compiled before their
import failing as nonfunctions. These were host-side tests, not a running
OpenWrt deployment.

At LuCI revision [`b2e0be4b46ec0fd43394c081fa7c50657af14011`](https://github.com/openwrt/luci/tree/b2e0be4b46ec0fd43394c081fa7c50657af14011),
the targeted source calls have exact inclusive spans:

| Source | Line and columns |
| --- | --- |
| `usr/share/rpcd/ucode/luci` (`getUSBDevices.call`) | 183:16–41 |
| `usr/share/rpcd/ucode/luci` (`getFeatures.call`) | 235:17–42 |
| `usr/share/ucode/luci/sys.uc` (`init_enabled`) | 142:14–27 |

The focused smoke stages these byte-hash-checked files and 74 independent
controls into an actual extraction database. It checks routing, the successful
extraction set, the malformed file's diagnostic and recovered call, and exact
call entity URLs and spans for the three pinned sites, nine supported controls,
and 14 explicitly unresolved call sites. The latter include both inside and
after-loop sites for ordinary/alternative key binders and an alternative
single-variable binder. Other negative controls include aliases,
absent/wrong/escaped imports, source order, shadows, writes, malformed and
compiler-invalid inputs, optional and non-identifier callees. Parse success
is not treated as compiler success.

The oracle was checked against real counterfactual queries in isolated pack
copies: replacing the `getFeatures` entity with the actual `readfile` entity
at 121:18 while keeping its labels and row count was rejected, as was replacing
the raw-source guard with the fragment-concatenating helper (which introduced
an `escaped_wrong_module.uc` target). A second independent review found five
additional surviving mutations in that earlier test set. With separate fixtures,
real query runs now reject deletion of just the extra-string-child guard,
the default-import count arm, the namespace-import count arm, both loop-key
arms, or the alternative loop-variable arm. These mutations add the exact
counterexample sites to the output; the loop mutations widen both the shadowed
and after-loop calls. The `'fs\x2fother'` fixture specifically starts with the
raw `fs` fragment and resolves to a harmless non-fs module in a host runtime
probe. In that runtime the duplicate default imports were compiler-rejected,
while the duplicate namespace form reached the call and failed as noncallable;
the loop probes caught the inner noncallable shadow and then used the native
import after the loop. These observations do not establish deployed behavior.
No production readfile matcher, taint
source/sink, sanitizer, through-flow, runtime target, or security query is
changed. `propagatesFlow` remains `none()`; this slice does not establish a
consumer security finding, `path_found`, or deployed runtime behavior.

Reproduce after the README bootstrap with
`bash scripts/m4-imported-fs-readlink-smoke.sh`; the aggregate discovers it
once via `scripts/m4-*-smoke.sh`.
