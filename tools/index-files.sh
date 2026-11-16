#!/bin/sh

set -eu

if [ -n "${CODEQL_UCODE_STAGED_ROOT:-}" ]; then
    set -- "$1" --staged-root "$CODEQL_UCODE_STAGED_ROOT"
fi

exec "${CODEQL_EXTRACTOR_UCODE_ROOT}/tools/${CODEQL_PLATFORM}/extractor" \
        extract \
        --file-list "$@" \
        --source-archive-dir "$CODEQL_EXTRACTOR_UCODE_SOURCE_ARCHIVE_DIR" \
        --output-dir "$CODEQL_EXTRACTOR_UCODE_TRAP_DIR"