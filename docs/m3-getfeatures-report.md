# M3 evidence: `/ubus` `luci.getFeatures`

Findings are evidence, not proof. Wrapper AST/CFG/dataflow libraries are not imported; models walk generated TreeSitter nodes.

## Selected chain

`getFeatures.call` → same-file `callPackageVersionCheck('netifd')` → named `popen` imported from `'fs'` (opkg and apk branches).

The Models helper association only accepts a direct non-optional identifier call
following a complete top-level function declaration in the same error-free file.
Every same-name identifier must be the selected declaration's name or a direct
call callee; shorthand properties also veto it. Competing bindings, writes and
aliases anywhere in the file intentionally suppress associations, including in
unrelated scopes or later source text. A missing association means unknown, not
safe or unreachable. This is syntactic evidence, not lexical or runtime target
resolution; descendant sink matches also do not establish execution of nested
functions.

That is a **syntactic helper/sink association**, recorded as `handler_effect` / `fact` (`GetFeaturesPopen.ql`); it does not prove runtime reachability or a taint path. Pairwise syntactic local taint from `request.args` into that helper is **`taint_path` / `no_path`** (the pinned `GetFeaturesHelperTaint.ql` result was empty).

Assessment for stock unauthenticated feature probing: **intended_access**. The helper interpolates a literal package name through `shellquote`. Reaching `popen` here is not BAC or RCE.

## Synthetic taint controls

| Fixture | Expected | Result |
| --- | --- | --- |
| `taint_pos` | `request.args.cmd` → `popen` | `path_found` |
| `taint_neg` | unused `request.args.cmd`; `popen` of a fixed string | `no_path` |

## Other luci `popen` / `system` (unassessed)

Nine named `fs` `popen` calls and six builtin `system()` calls exist in the plugin. Four `popen` sites take `request.args` (switch helpers). Those methods are **unassessed** in this slice. `getFeatures` also calls builtin `system()` for hostapd/wpa_supplicant probes (template strings); expected-capabilities already lists them as unmodeled branches.

## Coverage

See `docs/m3-coverage.json`. M2 `policy/grants.json` records unauthenticated `luci.getFeatures` as `intended_access`. The join with those grants is `corpus_revision` (`sha256:b4cbdabb…` of codeql-openwrt `corpus/lock.json`) plus `profile` and `entrypoint_id`; `analysis_revision` stays producer-local (`policy:ubus-getfeatures-v1` vs `step3:getfeatures-v1`). This pack does not claim a live daemon run or a plugin-side session check.
