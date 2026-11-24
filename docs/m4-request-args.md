# M4 evidence: luci `request.args` → `popen` / `system`

Findings are evidence, not proof. Models walk generated TreeSitter nodes plus same-function name bindings. Wrapper AST/CFG/SSA libraries are not imported. `shellquote` is observed in the query message; it is **not** a modeled sanitizer.

## Methods

| Method | Sink | Param | Quoting | ACL source (not M2-emitted) |
| --- | --- | --- | --- | --- |
| `getSwconfigFeatures` | named `popen` `swconfig` | `switch` | `shellquote` in the sink argument | `luci-mod-network-config` read |
| `getSwconfigPortState` | named `popen` `swconfig` | `switch` | `shellquote` in the sink argument | `luci-mod-network-config` read |
| `getRealtimeStats` | named `popen` `luci-bwc` | `device` | `shellquote` into local `flags` | `luci-mod-status-realtime` read |
| `setPassword` | builtin `system` `passwd` | `username`, `password` | `shellquote` into locals `u`/`p` | `luci-mod-system-config` write |
| `setLocaltime` | builtin `system` `date` | `localtime` | none; `localtime()` then `sprintf %d` | `luci-mod-system-config` write |

Unauthenticated `/ubus` still only grants `luci.getFeatures` (M2). These five methods are **not** unauthenticated. This slice does not emit `authorization_violation`. Delegated module sessions are `unassessed` until policy-facts emit those grants.

`getFeatures` is absent from `RequestArgsExec.ql` (negative control). The query retains the legacy `luci` basename and additionally accepts seven exact source-root-relative installed paths under `usr/share/rpcd/ucode/`: `docker_rpc.uc`, `ddns.uc`, `tailscale.uc`, `example.uc`, `rustdesk-server.uc`, `wifihistory.uc`, and `weechat.uc`. Other paths, including package-layout paths for those basenames, are not included by this additional eligibility rule. Synthetic `taint_pos` / `taint_neg` remain excluded. Eligibility alone does not establish that an application has a modeled flow or a security finding; the existing Models method, source, sink and local-taint constraints still apply.

See `docs/m4-coverage.json`.

## Still unmodeled in this slice

- `setInitAction` → `init_action(request.args.*)` (interprocedural)
- `getFeatures` hostapd/wpa_supplicant `system()` templates and dnsmasq/odhcpd/ipset `popen`
- `shellquote` as a complete-argument barrier
- full CFG/SSA and global flow
