# M4: `request.args` into imported callees

`setInitAction.call` forwards `request.args.name` and `request.args.action` to `init_action` imported from `'luci.sys'`. M1/M3 still index `luci` / taint fixtures only. `m4-sys-smoke.sh` extracts `sys.uc`, but DataFlow `viableSourceCallable` is `none()`, so the import is still not a resolved callee. Same-file Models taint stops at the call.

Evidence: `taint_path` / `inconclusive` (`unresolved_call`). This is not `no_path`, not DataFlow `path_found`, and not a demonstrated sink. `SsaReachesSystem.ql` does not score luci.

See `docs/m4-imported-callee-findings.json`.
