#!/usr/bin/env bash
# Fresh installed-stage extraction and default-suite SARIF on two retained IPKs.
set -euo pipefail

: "${DIRECT_RPC_RUN_DIR:?}"
: "${CODEQL_BIN:?}"
: "${GH_TOKEN:?}"

root="$DIRECT_RPC_RUN_DIR/r25"
test ! -e "$root"
mkdir -p "$root/ipk/luci" "$root/ipk/wifi"
gh run download 45513606386 -R lucas-albers-lz4/codeql-openwrt \
  -n luci-ipk-byte-45513606386-1 -D "$root/ipk/luci"
gh run download 45548269425 -R lucas-albers-lz4/codeql-openwrt \
  -n wifi-ipk-byte-45548269425-1 -D "$root/ipk/wifi"

bundle="$DIRECT_RPC_RUN_DIR/verified-bundle/codeql-ucode-linux"
test -f "$bundle/bundle-manifest.json"
manifest_sha="$(sha256sum "$bundle/bundle-manifest.json" | cut -d ' ' -f 1)"

python3 scripts/stage-installed-ipk.py \
  --ipk "$root/ipk/luci/luci-base.ipk" \
  --ipk-sha256 1a2188f5206ce61c993fdcc451781a06994ae2175b489eef56595858ef22b363 \
  --oracle tests/fixtures/r25-installed-stage/luci-base-oracle.json \
  --output "$root/stage-luci" > "$root/stage-luci-receipt.json"
python3 "$bundle/runner/run-installed-stage.py" \
  --bundle "$bundle" --bundle-sha256 "$manifest_sha" \
  --codeql "$CODEQL_BIN" --stage "$root/stage-luci" \
  --oracle tests/fixtures/r25-installed-stage/luci-base-oracle.json \
  --output "$root/run-luci"

python3 scripts/stage-installed-ipk.py \
  --ipk "$root/ipk/wifi/y-wifi-scripts.ipk" \
  --ipk-sha256 20f2e18297a10e2c2fc0f3457dee52e5ee2db01a8d17d52ba44dffaf79ba833a \
  --oracle tests/fixtures/r25-installed-stage/wifi-scripts-ucode-y-oracle.json \
  --output "$root/stage-wifi" > "$root/stage-wifi-receipt.json"
python3 "$bundle/runner/run-installed-stage.py" \
  --bundle "$bundle" --bundle-sha256 "$manifest_sha" \
  --codeql "$CODEQL_BIN" --stage "$root/stage-wifi" \
  --oracle tests/fixtures/r25-installed-stage/wifi-scripts-ucode-y-oracle.json \
  --output "$root/run-wifi"
