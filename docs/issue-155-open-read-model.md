# Source-declared literal-read `fs.open` association

`SourceDeclaredFsOpenReadCall` identifies a direct, non-optional, unaliased
source-declared `fs.open` call with two or three non-spread expression
arguments and a mode at index 1 consisting of one string fragment with value
`r`. It exposes the raw path at index 0, mode at index 1 and optional third
expression at index 2. Omitted mode, dynamic or other modes, extra arguments,
spread and other nonmatches are inconclusive. The third expression is not
validated as a runtime integer or effective permission. Whole-file competing-name
exclusions are conservative and do not prove lexical or runtime callee binding.
This association adds no flow, handle, Concepts sink, sanitizer, authorization,
`path_found` or security result, and does not change the default security suite.

The pinned [LuCI UPnP source](https://github.com/openwrt/luci/blob/b2e0be4b46ec0fd43394c081fa7c50657af14011/applications/luci-app-upnp/root/usr/share/rpcd/ucode/luci.upnp#L24)
contains `open(uci.get(...), 'r')`. Its source and the controls are recorded in
the [source-first manifest](../ql/test/issue155-open-read/manifest.json); the
[fixture attribution](../ql/test/luci-fixture-attribution/README.md) records
its source and license. The adjacent `leasefile.read` calls are outside this
model. The native `fs.open` implementation documents `r` as read mode, but this
model establishes the literal source shape only, not a successful open.

`scripts/m4-open-read-model-smoke.sh` stages the real source and controls, checks
routing, archive and diagnostics, witnesses raw AST and import/argument edges,
and compares exact class membership and argument identities. Counterfactuals
exercise the mode, argument slots, arity, spreads and source-attribution guards;
the `r` and `wx` calls in one file are checked as distinct associations.
Synthetic controls do not establish compiler or runtime acceptance. A passing
smoke does not establish application-scope flow or a security finding.
