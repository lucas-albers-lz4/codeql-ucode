#!/usr/bin/env bash
# Source from a smoke after setting ROOT. Only ci-ql-smoke.sh exports readiness.
install_smoke_packs() {
	if [[ "${CODEQL_UCODE_SMOKE_PACKS_READY:-}" == "$ROOT" ]]; then
		return 0
	fi
	codeql pack install "$ROOT/ql/lib" >/dev/null || return "$?"
	codeql pack install "$ROOT/ql/src" >/dev/null || return "$?"
}
