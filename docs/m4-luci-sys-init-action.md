# M4: extract luci.sys `init_action`

Installed path: `/usr/share/ucode/luci/sys.uc` (luci `openwrt-25.12` `@b2e0be4`). Extractor glob is the literal basename `sys.uc`. M1/M3 still index `luci` / taint fixtures only.

`export function init_action(name, action)` reaches builtin `system` with a template string that interpolates `basename(name)` and `action`. This query does **not** treat `basename` as a sanitizer and does not model `shellquote`. Interprocedural taint from `setInitAction` `request.args` is out of this slice.

`setInitAction.call` switches on `request.args.action` tokens `enable|disable|start|stop|restart|reload` (plus default). That is caller-side inventory, not a sanitizer of `name`.

See `InitActionSystem.ql`, `SetInitActionActionSwitch.ql`, and `scripts/m4-sys-smoke.sh`.
