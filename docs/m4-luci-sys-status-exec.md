# M4: luci.sys `conntrack_list` / `process_list` fixed popen

`ql/src/m4/LuciSysStatusExec.ql` inventories two named `popen` sinks in the
installed `sys.uc` fixture. The rpcd methods `getConntrackList` and
`getProcessList` only call the imported helpers; they do not take `request.args`.

| RPC method | Helper | Sink | Line |
| --- | --- | --- | --- |
| `getProcessList` | `process_list` | `popen('/bin/busybox top -bn1')` | 7 |
| `getConntrackList` | `conntrack_list` | fallback `popen('/usr/sbin/conntrack -L -o extended')` | 49 |

The conntrack popen runs only when `open('/proc/net/nf_conntrack')` fails; that
`file_read` path is out of scope here. This query does not treat `shellquote` or
`basename` as sanitizers and does not claim interprocedural `path_found` from
the `luci` plugin into `luci.sys`.

OpenWrt `handler_effect` / grant rows for these methods live in
[codeql-openwrt](https://github.com/lucas-albers-lz4/codeql-openwrt)
`reports/m4-luci-sys-status-exec.md` (draft PR #16). This pack query is the
extractor gate those rows were transcribed against.
