# OpenVPN raw metadata regression

`parent.uc` and `fixed.uc` are byte-exact copies of the LuCI source at the
commits and path in `expected.json`. The other four files derive from the
parent: a constant sink, reassigned request formal, shadowed sink `cmd`, and
uncalled nested assignment. Stage each file alone as
`usr/share/rpcd/ucode/luci.openvpn.uc` in its own CodeQL database. The query
`ql/src/m4/OpenvpnRawMetadataCommand.ql` requires this installed-style path.

Check `SuccessfullyExtractedFiles.ql` and `ExtractionErrors.ql` first. Then
check the exact source and sink spans and result multiplicity in
`expected.json`. The vulnerable parent has one raw-substitution result; the
real fix and four eligible near misses have none. The fixed source
retains the request access and sink, so a zero result is a change in the
interpolation shape rather than missing extraction.

This experimental rule recognizes only direct raw interpolation into a
branch-assigned `cmd` followed by imported `fs.popen(cmd)` in the same RPC
method. Conservative same-body and local-binding guards exclude the tested
shadow and nested-callable shapes; they are not a general lexical resolver or
data-flow engine. This rule does not prove the local `shellquote` implementation is safe, or
that an unreported source is safe. Broader flow, helper binding, path changes,
installed-byte provenance, runtime reachability, and SARIF/default-suite
promotion require separate evidence.
