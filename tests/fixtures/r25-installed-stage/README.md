# Pinned installed-stage package oracles

These source-first expectations were prepared from actual retained IPK member
bytes before any R2.5 CodeQL output was inspected. `luci-base-oracle.json`
lists all 76 regular `data.tar.gz` members: 10 plain routes, eight
markup/inconclusive routes and 58 exclusions. `wifi-scripts-ucode-y-oracle.json`
lists all 31 regular members: 17 plain routes and 14 exclusions. Paths are
relative to an installation-shaped stage, and hashes refer to IPK member
bytes. The runner must compare exact routing and successful-file identities,
including multiplicity; these JSON files are expectations, not observations.

| Package | Retained OpenWrt Actions source | Whole IPK SHA-256 |
| --- | --- | --- |
| `luci-base` `26.284.22350~8125d12` (`x86_64`) | Run `45513606386`, artifact `luci-ipk-byte-45513606386-1` (`14979253876`) | `1a2188f5206ce61c993fdcc451781a06994ae2175b489eef56595858ef22b363` |
| `wifi-scripts` `1.0-r1` (`all`, `CONFIG_WIFI_SCRIPTS_UCODE=y`) | Run `45548269425`, artifact `wifi-ipk-byte-45548269425-1` (`14997815607`) | `20f2e18297a10e2c2fc0f3457dee52e5ee2db01a8d17d52ba44dffaf79ba833a` |

The pinned OpenWrt source revision is
`4e9642517b48bae612ff10fb72fb9199e559500e`; LuCI is
`b2e0be4b46ec0fd43394c081fa7c50657af14011`; the packages feed is
`07e0d16305d2b5903b37ad7913e33e18795f81a4`. Route expectations were
derived from `extractor/src/extractor.rs` at Git blob
`6a94c6ab472fb8aa4610fa8d6e9ee5eaf2656349`, SHA-256
`bc54d2fc6e4dfba095977053d92275c3474bb01ff7e6da7c5301002bde701a11`.
That routing source was identical at inspected producer heads
`977b3fed209fffc68cdfcf9e558c8bbe9ee728f9` and
`b97323a510cc6920c462d0381c26a1b9e03e5403`.

The `luci-base` IPK contains two extensionless Ucode files:
`usr/share/rpcd/ucode/luci` and `www/cgi-bin/luci`. Its eight markup files
are expected successful extraction identities but remain inconclusive for
model coverage. `template/header.ut` has installed package bytes changed by
version substitution, and `version.uc` is generated. Their hashes in the
oracle are the actual IPK member hashes, not source-tree hashes. The
`wifi-scripts` Ucode-enabled IPK includes Ucode-shebang
`lib/netifd/wireless/mac80211.sh` and extensionless `usr/bin/iwinfo`; the
Ucode-disabled package provides a separate shell-script near miss at the
same `mac80211.sh` path but is not scanned by this two-package gate.

The IPK artifacts are retention-limited. The gate requires their exact whole
archive hashes and checks every regular member before staging. This shows
package-member bytes at installation-shaped paths, not installation on a
device. Durable fixture custody or a fresh verified build will be needed for
routine retests after the artifacts expire.
