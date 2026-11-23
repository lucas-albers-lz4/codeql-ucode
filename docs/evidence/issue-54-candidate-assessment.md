# Issue 54 candidate assessment

Assessment at ucode `11a53fd8e911573860950ee8e549b337a8742438`; OpenWrt `0fe3ba01265384d52953289f324113ee2c9e38cc`. [Issue #54](https://github.com/lucas-albers-lz4/codeql-ucode/issues/54) requires each family’s model or habitation, query, controls and consumer acceptance. No new family is ready for promotion on this evidence. The owner’s 2026-11-18 census reported the five broad queries absent (counts N/A), `propagatesFlow` zero for all three summaries, and `ActiveThreatModelSource`, `FlowSource`, and `FlowSink` all zero. These are historical observations at that census pin, not newly measured counts at this assessment revision. Production taint migration remains held under its separate gate.

| Family | Readiness and next prerequisite |
| --- | --- |
| HandlerEffects | Existing bounded getBlockDevices and setBlockDetect observations and setLocaltime construction are not the broad query. Select a distinct supported effect with an established model, exact controls and consumer acceptance. |
| CommandInjection | Strongest investigation candidate below; establish supported static path semantics and independent controls, then agree consumer acceptance. Existing syntactic tests do not provide a promoted path query. |
| ExecGrantGlob | No broad query in the census; establish a supported execution/grant model and a candidate or risky-delegation consumer contract with relevant matching and nonmatching controls. |
| BrokenAccessControl | Requires modeled effect plus an explicit expectation and a policy consumer; establish those for a distinct case before interpreting access. |
| MissingLocalGuard | Requires applicable guard/effect modeling and a candidate/inconclusive consumer contract; establish controls before staffing. No BAC follows from missing observations. |

## Candidate and existing consumer

In pinned LuCI source `usr/share/rpcd/ucode/luci`, `getSwconfigFeatures` line 343 and `getSwconfigPortState` line 400 each place `request.args.switch` inside the `popen` command argument through `shellquote`. `Models.qll`'s `taintReachesSink` uses AST containment or same-method name-based initializer/assignment chains; it is not CFG/SSA and does not distinguish later reassignments. Both examples use direct containment. `ShellInjection.ql` reports candidates under that relation and does not treat the locally defined `shellquote` as a trusted barrier. This does not prove an executable path, actual execution, injection, or a security conclusion.

The existing `scripts/m4-quote-smoke.sh` source asserts the seven tuples below, a positive `taint_pos`, negative `taint_neg`, and quoting controls; those synthetic controls were **not rerun here**. The OpenWrt pin already contains historical `reports/m4-findings.json` records labeled `taint_path` / `path_found` for the two methods, explicitly qualified as syntactic local taint rather than CFG/SSA. Its `reports/handler_effects.json` rows say they were projected from those records, not a new query run; `policy/grants.json` and expectations provide existing associations. These labels do not establish new path semantics or acceptance of a new family. A candidate-only adapter may repeat those records; agree a concrete incremental consumer contract before implementing one, without changing grants or inferring authorization.

## Focused query comparison

A copy of `/private/tmp/openwrt-typed-handoff-live-20261123/retry-run/database` was queried using the assessment revision’s query and library files, CodeQL CLI 2.27.4, the prior staged dependency packs and fresh compilation/common caches. This is a **requery of a prior pinned extraction**, not a fresh extraction. The previous bounded typed handoff’s actual run was independently audited; later post-merge findings concerning the reusable runner remain open and do not by themselves establish that this particular run was invalid. This requery does not attest execution provenance or repair those findings.

The retained successful-file CSV identifies only `/private/tmp/openwrt-typed-handoff-live-20261123/source/usr/share/rpcd/ucode/luci`; the retained errors CSV has only its header. The source archive contains exactly one file and its SHA-256, the retained input source hash, and the main fixture hash all equal `6f9d972958d9cfb8a7ba421f38f0a5b03718ffeb0e30d460b64c9faf725fc54e` (LuCI revision `b2e0be4b46ec0fd43394c081fa7c50657af14011`). Database and main library dbscheme hashes both equal `a32b8f63d4545439bc632b4afd0d58ad64aa2a634736bcd341fba68b7690ad2b`. Schema hash equality is a compatibility check, not proof of extraction correctness.

The successful commands and environment are in [commands.json](issue-54-candidate-assessment/commands.json); working directory was `/private/tmp/ucode-issue54-assessment`. The first attempt, from a copied pack layout, failed workspace dependency resolution with exit 2; its [command](issue-54-candidate-assessment/failed-commands.json) and [stderr](issue-54-candidate-assessment/failed-query.stderr) are retained. The retry used the main paths and succeeded. BQRS, query stderr, retained extraction diagnostics and two separately invoked byte-identical CSV decodes are in the adjacent evidence directory. Both successful queries warned that the qlpack commit hash could not be retrieved and that query-loading stages were not cached with the 1256 MB maximum heap. ShellInjection also warned that a problem query must select an even number of columns; it selected seven. Both commands exited zero, but were not warning-free. Results are local observations, not authenticated or fresh extraction evidence.

`ShellInjection` yielded exactly this expected multiset of `(method, sink, sink line, source line)`, matching the existing smoke oracle:

```text
setLocaltime system 111 108
getSwconfigFeatures popen 343 343
getSwconfigPortState popen 400 400
setPassword system 474 470
setPassword system 474 471
getRealtimeStats popen 585 575
getRealtimeStats popen 585 577
```

`RequestArgsExec` returned seven rows with matching method/sink multiplicities. Its CSV does not expose source or sink coordinates, so this comparison does not establish full tuple identity for that query. Neither query run exercises synthetic negatives or establishes absence outside the single extracted source. `ShellInjection.decode.stdout` SHA-256 `c3df87b9f70a945867e2c4a7d9ec6c5bb48126d501f012e4db07dc2906ab21d7`; `RequestArgsExec.decode.stdout` SHA-256 `91cb98a05bf8a7086f2f6814aba6c629745047a15bcaff60c11fbcbe47ce96e0`.

The bounded receiver table identifies source-declared receiver provenance, not runtime targets or taint; the retained direct-copy experiment produced 17 to 17 real rows. The bounded markup CFG work does not establish general markup flow. The UCI helper observation and typed setBlockDetect handoff describe narrowly pinned source observations, not general UCI semantics or a new broad family. These additions do not satisfy the prerequisites above. Nonmatches, unknown callees, unsupported forms and extraction failures remain inconclusive.
