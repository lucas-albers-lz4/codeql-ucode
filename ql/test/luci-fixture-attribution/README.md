# LuCI source fixture attribution

The following files are copied byte-for-byte from the OpenWrt LuCI repository
at the commits linked below:

| Local fixture | Upstream source | Git blob | SHA-256 |
| --- | --- | --- | --- |
| [`ddns.uc`](../issue155-stat-observation/usr/share/rpcd/ucode/ddns.uc) | [`applications/luci-app-ddns/root/usr/share/rpcd/ucode/ddns.uc`](https://github.com/openwrt/luci/blob/b2e0be4b46ec0fd43394c081fa7c50657af14011/applications/luci-app-ddns/root/usr/share/rpcd/ucode/ddns.uc) | `32d1da738b4932159a39bcda7ee6c72b5c58a8fd` | `924bd2b53fbc64d2a00a479e36ef3c9239488445fc1ced70122e8ac3735fdc2b` |
| [`weechat.uc`](../issue155-rename/usr/share/rpcd/ucode/weechat.uc) | [`applications/luci-app-weechat/root/usr/share/rpcd/ucode/weechat.uc`](https://github.com/openwrt/luci/blob/b2e0be4b46ec0fd43394c081fa7c50657af14011/applications/luci-app-weechat/root/usr/share/rpcd/ucode/weechat.uc) | `9f17ae3718a278eab2813ccfae4f2c732a9118e8` | `548213868a38bd84d8a9cb9b9842c647d4e79fa9df21b815b6b869f26a54e44e` |
| [`luci.openvpn.uc`](../issue155-mkdir/usr/share/rpcd/ucode/luci.openvpn.uc) | [`protocols/luci-proto-openvpn/root/usr/share/rpcd/ucode/luci.openvpn.uc`](https://github.com/openwrt/luci/blob/8d1aecd0216a02ad52c830e9a03c21da734bf630/protocols/luci-proto-openvpn/root/usr/share/rpcd/ucode/luci.openvpn.uc) | `eb3b418f855d24ae0a34d5d09a289b9342098129` | `6593792678951fd500c2b090d17d9e500a05a642cfb996ee02c1649473152410` |

At the earlier commit both package Makefiles declare `PKG_LICENSE:=Apache-2.0`:
[DDNS](https://github.com/openwrt/luci/blob/b2e0be4b46ec0fd43394c081fa7c50657af14011/applications/luci-app-ddns/Makefile)
and [WeeChat](https://github.com/openwrt/luci/blob/b2e0be4b46ec0fd43394c081fa7c50657af14011/applications/luci-app-weechat/Makefile).
The adjacent [LICENSE](LICENSE) and [NOTICE](NOTICE) reproduce the LuCI root
files from the same commit, Git blobs `f49a4e16e68b128803cc2dcea614603632b04eac`
and `2136dbbf0a113a05ae8f1f766b3bd5d5ababac9e`, respectively. The notice is
included in full as upstream provided it; this attribution does not assert that
every third-party component named there appears in these fixtures. The same license and notice blobs occur at the OpenVPN source pin; its [package Makefile](https://github.com/openwrt/luci/blob/8d1aecd0216a02ad52c830e9a03c21da734bf630/protocols/luci-proto-openvpn/Makefile) declares `PKG_LICENSE:=Apache-2.0`.
