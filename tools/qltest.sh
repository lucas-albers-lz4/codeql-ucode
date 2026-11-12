#!/bin/sh

set -eu

"${CODEQL_DIST}/codeql" database index-files \
    --prune="**/*.testproj" \
    --include-extension= \
    --size-limit=5m \
    --language=ucode \
    --working-dir=.\
    "$CODEQL_EXTRACTOR_UCODE_WIP_DATABASE"

exec "${CODEQL_DIST}/codeql" database index-files \
    --prune="**/*.testproj" \
    --include-extension=.yml \
    --include-extension=.yaml \
    --include-extension=.json \
    --size-limit=5m \
    --language=yaml \
    --working-dir=.\
    "$CODEQL_EXTRACTOR_UCODE_WIP_DATABASE"