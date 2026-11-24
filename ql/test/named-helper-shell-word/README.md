# Named helper shell-word experiment

`NamedHelperShellWord.ql` is a testing-tagged, explicit query. The default suite does not include it. The source-first LuCI oracle is the separate ledger artifact `work/luci-lldpd-helper-oracle/source-first-oracle.json`, SHA-256 `f269580b4cc3e17c37b5e9fe07836041173c3270c15a9982fd6a211f490556f9`. The pinned upstream source is `luci.lldpd` at LuCI `b2e0be4b46ec0fd43394c081fa7c50657af14011`, SHA-256 `a9d6e6477307408a130ce20ad9f92813dfeca611e5c8a5a7a86f2ca746081eac`.

Expected location-bearing candidates, fixed before querying:

| Input | Expected SARIF locations | Reason |
| --- | --- | --- |
| `luci.lldpd` | none | Four actuals at lines 13–16 are fixed strings. |
| `helper-dynamic-positive.uc` | 12:23–43 | Returned handler passes `request.args.section` to the helper formal. |
| `trailing_word_positive.uc` | 12:23–43 | Dynamic actual with a literal whitespace-delimited trailing word. The original dynamic fixture ends at the substitution. |
| `helper-fixed-literal-nearmiss.uc` | none | Matching returned handler passes a fixed string. |
| `duplicate_helper.uc` | none | Same-file helper target is ambiguous. |
| `helper_shadow.uc` | none | A local binding shadows the helper in the handler. |
| `helper_actual_shadow.uc` | none | A local binding shadows the request formal. |
| `loop_request_formal.uc` | none | A loop binds the request formal at the call inside the loop. |
| `loop_helper_formal.uc` | none | A loop binds the helper formal at the sink inside the loop. |
| `loop_helper_shadow.uc` | none | A loop binds the helper name at the call inside the loop. |
| `catch_helper_shadow.uc` | none | A catch binds the helper name in the handler. |
| `nested_helper_block.uc` | none | Helper declaration is nested in a top-level block. |
| `nested_table_block.uc` | none | Returned methods table is declared in a top-level block. |
| `nested_return_block.uc` | none | Return statement is nested in a top-level block. |
| `augmented_helper_write.uc` | none | An augmented assignment writes the helper name. |
| `updated_helper_write.uc` | none | An update writes the helper name. |
| `reassigned_formal.uc` | none | Helper formal is reassigned before the sink. |
| `sink_shadow.uc` | none | A local binding shadows imported `popen`. |
| `earlier_substitution.uc` | none | Earlier dynamic substitution can change quote context. |
| `quoted_word.uc` | none | Interpolation occurs inside literal quotes. |
| `word_fragment.uc` | none | Interpolation is part of a larger literal word. |

The source-first expectation was the two distinct positive locations above and zero results for all other files. File SHA-256 values were recorded by the run preflight before extraction and query output inspection. The original two oracle fixtures retain their exact upstream ledger hashes. The loop controls place the source read or call inside the loop, where the loop binding is active. Fresh isolated run-d under the ledger's ignored `work/helper-shell-run-d` extracted all 21 staged files exactly once, with no extraction errors. Its explicit query and SARIF emitted only the two expected locations. All 10 matrix commands exited zero; query time was 2.903 seconds, peak RSS 461,389,824 bytes, and SARIF time was 1.930 seconds. Run-local AST witnesses confirmed the two candidate chains, four real fixed-string actuals, nested-block declarations/return, and active in-loop uses. These raw artifacts are local and not portable evidence in this branch.

The model requires one direct Program-level same-file named helper, a direct Program-level methods table and return, a direct first actual/first formal edge, an unchanged formal, direct raw template use in imported `fs.popen`, and a returned `methods.<name>.call` shape. It does not establish RPC registration, runtime invocation, source reachability, shell quoting beyond literal boundaries, or vulnerability. It intentionally omits aliasing, multi-step propagation and nested helper calls.
