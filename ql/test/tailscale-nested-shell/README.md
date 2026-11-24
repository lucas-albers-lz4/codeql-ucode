# Tailscale nested shell regression inputs

`parent` and `fixed` are the unchanged mainline LuCI source bytes for
`applications/luci-app-tailscale-community/root/usr/share/rpcd/ucode/tailscale.uc`
at parent `46cd82328dfb7fbb15961c63f9e674a41cef2500` and fix
`507ab5e45c304543d4111af9a331db0f03be6bcb`. They are staged at the
package's installed-style ucode path. This does not authenticate installed
package bytes. The four `controls` are source-first fixtures from ledger claim
036. Their hashes and expected identities are in `expected.json`.

Run each stage in its own CodeQL database with the ucode extractor. Require
exactly one successful extraction per staged file and zero extraction errors.
For `TailscaleNestedShell.ql`, require one candidate at parent `popen`
164:3–48 and one at `nested_pos.uc` 18:5–50. Require no candidate on the
fixed file, `nested_fixed.uc`, `nested_near_miss.uc`, or `model_pos.uc`.
`model_pos.uc` is the separate direct-flow positive for `ShellInjection.ql`.
The supplemental controls `nested_reassigned.uc`, `nested_shadow.uc`,
`nested_helper_constant.uc`, and `nested_closure.uc` must also produce no row.
Three constant-first `||` controls retain the source read, push, join and
sink but select a constant value at the trim, push or command initializer;
each must produce no row.
The shadow control intentionally retains the outer tainted flow; its absence
shows the rule's conservative ambiguity cutoff, not a safety conclusion.
The two parent field paths (`loginserver` and `loginserver_authkey`) converge
on one sink and should be checked with a field witness, rather than treating
one output row as evidence for both paths.

The local `shell_quote` is a top-level declaration with direct calls, and its
body wraps the value in single quotes while replacing embedded single quotes.
It is **not** a barrier for expansion by the outer shell when the complete
`/bin/sh -c` argument uses double quotes. The rule checks direct binding via
`sameFileCall` and checks the return expression's quotation and `replace`
shape. It does not prove the global `replace` binding, the helper's runtime
behavior, or safe quotation in an arbitrary source file. Fixed-site absence
describes the query's literal outer form, not a safety result.
The query anchors its joins to a matching `popen` in one source file and
requires the supported declarations, push and sink on distinct ordered lines.
Same-line constructions are outside this bounded regression.
