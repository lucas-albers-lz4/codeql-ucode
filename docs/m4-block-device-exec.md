# M4: luci fixed `/sbin/block` and `sysfixtime` exec

`ql/src/m4/BlockDeviceExec.ql` inventories three plugin-body sinks in the
rpcd `luci` fixture (not `luci.sys`, not `request.args`):

| Method | Sink | Line |
| --- | --- | --- |
| `getBlockDevices.call` | named `popen` `/sbin/block info` | 481 |
| `setBlockDetect.call` | builtin `system` `/sbin/block detect` | 532 |
| `setLocaltime.call` | builtin `system` `/etc/init.d/sysfixtime restart` | 112 |

The `setLocaltime` `date -s` sink at line 111 stays on the request.args
inventory. This query does not treat `shellquote` or `basename` as
sanitizers and does not claim `path_found` or `setInitAction` taint.

OpenWrt reports for these rows live in
[codeql-openwrt](https://github.com/lucas-albers-lz4/codeql-openwrt)
`reports/m4-block-device-exec.md` (#15). This pack query is the extractor
gate those rows were transcribed against.

The query matches each complete command literal, including redirections. The
smoke verifies the fixture hash in `SOURCE.txt`, rebuilds its database from
current sources, and checks exact method/sink/command/line tuples.
