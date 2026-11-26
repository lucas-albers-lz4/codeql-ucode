#!/usr/bin/env bash
# Fresh installed-stage extraction and default-suite SARIF on two retained IPKs.
set -euo pipefail

: "${DIRECT_RPC_RUN_DIR:?}"
: "${DIRECT_RPC_TOOLS_DIR:?}"
: "${CODEQL_BIN:?}"
: "${GH_TOKEN:?}"

root="$DIRECT_RPC_RUN_DIR/r25"
test ! -e "$root"
mkdir -p "$root/ipk"
python3 scripts/download-pinned-r25-artifact.py \
  --run-id 45513606386 --artifact-id 14979253876 \
  --artifact-name luci-ipk-byte-45513606386-1 \
  --zip-sha256 cefdf043c269e61a6e13d2dbe9213898c8898f30b7d9413761d3a51c5d9c95da \
  --ipk-name luci-base.ipk \
  --ipk-sha256 1a2188f5206ce61c993fdcc451781a06994ae2175b489eef56595858ef22b363 \
  --output "$root/ipk/luci" > "$root/luci-artifact-receipt.json"
python3 scripts/download-pinned-r25-artifact.py \
  --run-id 45548269425 --artifact-id 14997815607 \
  --artifact-name wifi-ipk-byte-45548269425-1 \
  --zip-sha256 c52528d8bf453585cc5c384d1a573263db7a0102c2a9df443bee7a029869970a \
  --ipk-name y-wifi-scripts.ipk \
  --ipk-sha256 20f2e18297a10e2c2fc0f3457dee52e5ee2db01a8d17d52ba44dffaf79ba833a \
  --output "$root/ipk/wifi" > "$root/wifi-artifact-receipt.json"
unset GH_TOKEN GITHUB_TOKEN

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
  --codeql "$CODEQL_BIN" --codeql-archive "$DIRECT_RPC_TOOLS_DIR/download/codeql-linux64.zip" \
  --stage "$root/stage-luci" \
  --oracle tests/fixtures/r25-installed-stage/luci-base-oracle.json \
  --output "$root/run-luci"
jq -e '(.files | length) == 76 and
  ([.files[] | select(.route.classification == "excluded")] | length) == 58 and
  ([.files[].successful_count] | add) == 18 and
  ([.files[] | select(.route.status == "inconclusive")] | length) == 8' \
  "$root/run-luci/output/coverage-manifest.json"

python3 scripts/stage-installed-ipk.py \
  --ipk "$root/ipk/wifi/y-wifi-scripts.ipk" \
  --ipk-sha256 20f2e18297a10e2c2fc0f3457dee52e5ee2db01a8d17d52ba44dffaf79ba833a \
  --oracle tests/fixtures/r25-installed-stage/wifi-scripts-ucode-y-oracle.json \
  --output "$root/stage-wifi" > "$root/stage-wifi-receipt.json"
python3 "$bundle/runner/run-installed-stage.py" \
  --bundle "$bundle" --bundle-sha256 "$manifest_sha" \
  --codeql "$CODEQL_BIN" --codeql-archive "$DIRECT_RPC_TOOLS_DIR/download/codeql-linux64.zip" \
  --stage "$root/stage-wifi" \
  --oracle tests/fixtures/r25-installed-stage/wifi-scripts-ucode-y-oracle.json \
  --output "$root/run-wifi"
jq -e '(.files | length) == 31 and
  ([.files[] | select(.route.classification == "excluded")] | length) == 14 and
  ([.files[].successful_count] | add) == 17 and
  ([.files[] | select(.route.status == "inconclusive")] | length) == 0' \
  "$root/run-wifi/output/coverage-manifest.json"
