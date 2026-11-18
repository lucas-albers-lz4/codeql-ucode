#!/usr/bin/env bash
# Caller supplies ROOT, DB and QLPATH. M3 fallback checks still run separately.
check_m3_reuse_extraction() {
  local src="$ROOT/ql/test/extractor-smoke"
  python3 -B "$ROOT/scripts/m3-reuse-root.py" "$DB" "$src" || return "$?"
  source "$ROOT/scripts/m4-smoke-diagnostics.sh"
  check_m4_extraction "$src/taint_neg" "$src/taint_pos" "$src/usr/share/rpcd/ucode/luci"
}
