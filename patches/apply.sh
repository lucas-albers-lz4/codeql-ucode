#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
patch -p1 < patches/0001-language-ucode-and-luci-glob.patch
patch -p1 < patches/0002-tree-sitter-0.26.patch
patch -p1 < patches/0003-pack-names.patch
bash patches/0004-remove-php-import.sh
echo "M1 patches applied"
