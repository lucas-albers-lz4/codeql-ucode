# Named helper shell-word experiment

`NamedHelperShellWord.ql` is a testing-tagged, explicit query. The default suite does not include it. The source-first LuCI oracle is the separate ledger artifact `work/luci-lldpd-helper-oracle/source-first-oracle.json`, SHA-256 `f269580b4cc3e17c37b5e9fe07836041173c3270c15a9982fd6a211f490556f9`. The pinned upstream source is `luci.lldpd` at LuCI `b2e0be4b46ec0fd43394c081fa7c50657af14011`, SHA-256 `a9d6e6477307408a130ce20ad9f92813dfeca611e5c8a5a7a86f2ca746081eac`.

Expected location-bearing candidates, fixed before querying:

| Input | Expected SARIF locations | Reason |
| --- | --- | --- |
| `luci.lldpd` | none | Four actuals at lines 13–16 are fixed strings. |
| `helper-dynamic-positive.uc` | 12:23–43 | Returned handler passes `request.args.section` to the helper formal. |
| `terminal_word_positive.uc` | 12:23–43 | Same source shape, retained to test a template ending at the substitution. |
| `helper-fixed-literal-nearmiss.uc` | none | Matching returned handler passes a fixed string. |
| `duplicate_helper.uc` | none | Same-file helper target is ambiguous. |
| `helper_shadow.uc` | none | A local binding shadows the helper in the handler. |
| `helper_actual_shadow.uc` | none | A local binding shadows the request formal. |
| `reassigned_formal.uc` | none | Helper formal is reassigned before the sink. |
| `sink_shadow.uc` | none | A local binding shadows imported `popen`. |
| `earlier_substitution.uc` | none | Earlier dynamic substitution can change quote context. |
| `quoted_word.uc` | none | Interpolation occurs inside literal quotes. |
| `word_fragment.uc` | none | Interpolation is part of a larger literal word. |

A local isolated matrix in the ledger's ignored `work/helper-shell-run-b` directory extracted all 12 files once with zero diagnostics and produced exactly the two expected SARIF locations. The raw database and receipt are local run artifacts, not portable evidence in this branch. Query time was 2.674 seconds, peak RSS 415,891,456 bytes; explicit SARIF analyze took 1.826 seconds. `NamedHelperWitness` independently selected the two actual/formal/read/sink chains; `RealHelperAst` selected the four real fixed-string actuals and the imported sink. Both witness queries were run-local and are not part of this branch.

The model requires one top-level same-file named helper, a direct first actual/first formal edge, an unchanged formal, direct raw template use in imported `fs.popen`, and a returned `methods.<name>.call` shape. It does not establish RPC registration, runtime invocation, source reachability, shell quoting beyond literal boundaries, or vulnerability. It intentionally omits aliasing, multi-step propagation and nested helper calls.
