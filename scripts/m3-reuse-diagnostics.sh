#!/usr/bin/env bash
# Caller supplies ROOT, DB and QLPATH. Runs only on the reuse path: a fresh M3
# build already performed its own extraction checks.
check_m3_reuse_extraction() {
  local src
  src="$(cd "$ROOT/ql/test/extractor-smoke" && pwd -P)"
  python3 -B "$ROOT/scripts/m3-reuse-root.py" "$DB" "$src" || return "$?"
  source "$ROOT/scripts/m4-smoke-diagnostics.sh"
  check_m4_extraction "$src/taint_neg" "$src/taint_pos" "$src/usr/share/rpcd/ucode/luci"
}
