#!/usr/bin/env bash
# ast-internal.qll.jinja emits `private import codeql.php.ast.AstNodes`.
# Remove it from the generated tree before pack create.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
find "$ROOT/ql/lib" -name '*.qll' -print0 \
	| xargs -0 sed -i '/^private import codeql\.php\.ast\.AstNodes$/d'
